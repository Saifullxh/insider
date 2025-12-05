import google.generativeai as genai
import json
from typing import List, Dict, Optional

class LLMMapper:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        # List available models and use a valid one
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in str(m.supported_generation_methods)]
            print(f"Available Gemini models: {available_models[:5]}")
            
            # Prefer these models in order (free tier options)
            preferred = ['gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-1.5-flash']
            model_name = None
            
            for pref in preferred:
                for avail in available_models:
                    if pref in avail and 'exp' not in avail:  # Avoid experimental
                        model_name = avail
                        break
                if model_name:
                    break
            
            if not model_name and available_models:
                model_name = available_models[0]
            
            print(f"Using model: {model_name}")
            self.model = genai.GenerativeModel(model_name)
        except Exception as e:
            print(f"Error listing models: {e}")
            self.model = genai.GenerativeModel('gemini-2.0-flash')
    
    def map_news_to_markets(self, headline: str, markets: List[Dict]) -> List[Dict]:
        """
        Use Gemini to analyze a news headline and find relevant Polymarket markets.
        Returns a list of relevant markets with confidence scores.
        """
        market_titles = [m.get('title', '') for m in markets[:50]]
        
        prompt = f"""
You are an expert financial analyst and prediction market trader with deep knowledge of:
- Current macroeconomic conditions (interest rates, inflation, Fed policy, employment data)
- Geopolitical landscape (US-China relations, Middle East, Russia-Ukraine, trade policies)
- Cryptocurrency markets (BTC cycles, ETF flows, regulatory environment, institutional adoption)
- US political dynamics (2024 elections, congressional actions, policy shifts)
- Technology sector trends (AI, semiconductors, antitrust actions)

Today's date: December 2024. Use your knowledge of current events and economic conditions.

Your goal is to identify Polymarket prediction markets that are DIRECTLY influenced by this news, considering both the immediate impact AND the broader economic/political context.

News headline:
"{headline}"

Available prediction markets:
{json.dumps(market_titles, indent=2)}

Analysis framework:
1. What is the PRIMARY event or signal in this headline?
2. What is the current economic/political backdrop that amplifies or diminishes this signal?
3. Which markets have DIRECT causal exposure to this news?
4. How should probability estimates shift given BOTH the news AND current macro conditions?

For each selected market, provide:
- "market_title": exact title from the list  
- "relevance_score": 0.0-1.0 (only include if > 0.5)
- "reasoning": concise explanation linking news → mechanism → market outcome
- "direction": "increase" or "decrease" (YES probability)  
- "estimated_probability": your probability estimate (0.01-0.99) incorporating:
  • Base rates from historical precedent
  • Current market/economic sentiment
  • The specific news signal

Quality filters:
• Reject weak keyword matches with no causal mechanism
• Consider second-order effects (e.g., Fed policy → crypto → specific Bitcoin price targets)
• If news is bullish but market is already priced high, estimate accordingly
• Account for market efficiency - big news may already be priced in

Output: Return ONLY a valid JSON array. If no market is meaningfully affected, return [].
"""


        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            print(f"LLM Response: {text[:200]}...")
            
            # Clean up JSON if needed
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            
            mappings = json.loads(text.strip())
            
            # Match back to full market data
            results = []
            for mapping in mappings:
                for market in markets:
                    if market.get('title') == mapping.get('market_title'):
                        results.append({
                            **market,
                            'relevance_score': mapping.get('relevance_score', 0),
                            'reasoning': mapping.get('reasoning', ''),
                            'direction': mapping.get('direction', 'unknown'),
                            'estimated_probability': mapping.get('estimated_probability', None)
                        })
                        break
            
            return results
            
        except Exception as e:
            print(f"Error mapping news to markets: {e}")
            # Re-raise if it's a rate limit error so we can notify the user
            if "429" in str(e) or "quota" in str(e).lower():
                raise e
            return []
    
    def estimate_probability(self, headline: str, market: Dict) -> Optional[float]:
        """
        Use Gemini to estimate a probability for a market given news context.
        """
        market_title = market.get('title', '')
        current_prob = market.get('probability', 0.5)
        direction = market.get('direction', 'unknown')
        
        prompt = f"""News headline: "{headline}"

Market question: "{market_title}"
Current market probability: {current_prob}
Predicted direction based on news: {direction}

Based on this news, estimate the probability that this market resolves YES.
Consider: If the news says "{direction}" for this market, adjust your estimate accordingly.

Return ONLY a single decimal number between 0.01 and 0.99 (e.g., 0.75).
Do not return 0 or 1, always give a probability estimate."""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Clean up response - extract number
            import re
            numbers = re.findall(r'0?\.\d+|\d+\.?\d*', text)
            if numbers:
                prob = float(numbers[0])
                if prob > 1:
                    prob = prob / 100  # Handle percentage responses
                prob = max(0.01, min(0.99, prob))  # Clamp to valid range
                print(f"    Estimated probability: {prob}")
                return prob
            
            print(f"    Could not parse probability from: {text}")
            # Fallback: use current market prob adjusted by direction
            if direction == 'increase':
                return min(0.99, current_prob + 0.1)
            else:
                return max(0.01, current_prob - 0.1)
                
        except Exception as e:
            print(f"    Error estimating probability: {e}")
            # Fallback
            if direction == 'increase':
                return min(0.99, current_prob + 0.1)
            else:
                return max(0.01, current_prob - 0.1)
