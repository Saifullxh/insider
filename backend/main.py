from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager
import os
import asyncio

from llm_mapper import LLMMapper
from kelly_criterion import kelly_prediction_market, KellyResult
from polymarket_service import get_all_markets, get_user_positions
from wallet_service import wallet_service
from trading_service import trading_service
from news_service import news_service

# Initialize LLM
llm = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async lifespan for startup/shutdown."""
    global llm
    
    # Startup
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        llm = LLMMapper(api_key)
    else:
        print("WARNING: GEMINI_API_KEY not set. LLM features disabled.")
    
    # Initialize wallet (async)
    await wallet_service.initialize()
    
    yield
    
    # Shutdown
    print("Shutting down...")

app = FastAPI(title="Polymarket AI Trading Bot", lifespan=lifespan)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= Models =============

class NewsHeadline(BaseModel):
    headline: str
    source: Optional[str] = None
    timestamp: Optional[str] = None
    url: Optional[str] = None

class TradeProposal(BaseModel):
    market_id: str
    market_title: str
    direction: str
    bet_amount: float
    expected_edge: float
    reasoning: str
    approved: bool = False
    source_headline: Optional[str] = None
    source_url: Optional[str] = None

class ApprovalRequest(BaseModel):
    proposal_id: str
    approved: bool

# ============= In-Memory State =============

pending_proposals: List[TradeProposal] = []

# ============= Endpoints =============

@app.get("/")
async def root():
    return {"status": "Polymarket AI Trading Bot running"}

@app.get("/api/markets")
async def list_markets(limit: int = 50):
    """Get active Polymarket markets."""
    markets = get_all_markets(limit)
    return {"markets": markets}

@app.post("/api/analyze")
async def analyze_news(news: NewsHeadline, bankroll: float = None):
    """
    Analyze a news headline and find trading opportunities.
    If bankroll is not provided, uses actual wallet balance.
    """
    global llm, pending_proposals
    
    if not llm:
        raise HTTPException(status_code=500, detail="LLM not configured")
    
    # Use wallet balance if bankroll not specified (async)
    if bankroll is None:
        if wallet_service.is_configured():
            bankroll = await wallet_service.get_balance("usdc")
            # Fallback to simulated bankroll if balance is 0 (testnet mode)
            if bankroll == 0:
                bankroll = 100.0  # Simulated $100 for testnet
                print(f"Testnet mode - using simulated bankroll: ${bankroll}")
            else:
                print(f"Using wallet balance as bankroll: ${bankroll}")
        else:
            bankroll = 100.0
            print(f"Wallet not configured, using default bankroll: ${bankroll}")
    
    # Get markets
    markets = get_all_markets(100)
    print(f"Got {len(markets)} markets for analysis")
    
    if not markets:
        return {
            "headline": news.headline,
            "proposals": [],
            "message": "No active markets found. API may be unavailable."
        }
    
    # Map news to markets
    print(f"Mapping headline to markets: {news.headline}")
    try:
        mappings = llm.map_news_to_markets(news.headline, markets)
        print(f"LLM found {len(mappings)} relevant markets")
    except Exception as e:
        print(f"LLM Error: {e}")
        if "429" in str(e) or "quota" in str(e).lower():
            return {
                "headline": news.headline,
                "proposals": [],
                "message": "⚠️ AI Rate Limit Exceeded. Pausing analysis."
            }
        return {
            "headline": news.headline,
            "proposals": [],
            "message": "Error analyzing news."
        }
    
    proposals = []
    for market in mappings:
        # Use estimated probability from mapping if available, otherwise fetch it
        estimated_prob = market.get('estimated_probability')
        
        if estimated_prob is None:
            print(f"  Fetching probability for '{market.get('title', '')[:50]}'")
            estimated_prob = llm.estimate_probability(news.headline, market)
        
        if estimated_prob is None:
            print(f"  Market '{market.get('title', '')[:50]}' - no probability estimate")
            continue
        
        market_prob = market.get('probability', 0.5)
        
        print(f"  Market: '{market.get('title', '')[:50]}'")
        print(f"    Market price: {market_prob:.2f}, Estimated prob: {estimated_prob:.2f}")
        
        # Use new kelly_prediction_market function
        kelly = kelly_prediction_market(bankroll, market_prob, estimated_prob)
        
        # Check if we should bet (side is not NONE and bet amount > 0)
        if kelly.side != "NONE" and kelly.bet_amount >= 0.10:
            print(f"    Kelly: {kelly.side} ${kelly.bet_amount} (edge: {kelly.edge:.2%})")
            proposal = TradeProposal(
                market_id=market.get('id', ''),
                market_title=market.get('title', ''),
                direction=kelly.side,  # Use Kelly's recommended side
                bet_amount=kelly.bet_amount,
                expected_edge=kelly.edge * 100,  # Convert to percentage
                reasoning=market.get('reasoning', ''),
                approved=False,
                source_headline=news.headline,
                source_url=news.url
            )
            proposals.append(proposal)
    
    # Deduplicate: Keep only the best proposal per market (highest edge)
    best_proposals = {}
    for p in proposals:
        if p.market_id not in best_proposals or p.expected_edge > best_proposals[p.market_id].expected_edge:
            best_proposals[p.market_id] = p
    
    # Filter out proposals that already exist in pending
    existing_ids = {p.market_id for p in pending_proposals}
    new_proposals = [p for p in best_proposals.values() if p.market_id not in existing_ids]
    
    pending_proposals.extend(new_proposals)
    
    return {
        "headline": news.headline,
        "proposals": [p.dict() for p in new_proposals],
        "message": f"Found {len(new_proposals)} trading opportunities. Awaiting manual approval."
    }

@app.get("/api/news/headlines")
async def get_headlines(limit: int = 15, topic: str = "ALL"):
    """
    Fast endpoint: Just fetch headlines without AI analysis.
    Used for live news feed refresh.
    """
    headlines = news_service.fetch_news(limit=limit, topic=topic)
    return {"headlines": headlines, "count": len(headlines)}

@app.get("/api/news/scan")
async def scan_news(limit: int = 5, topic: str = "ALL"):
    """
    Fetch latest news and analyze all of them.
    Returns aggregated proposals.
    """
    headlines = news_service.fetch_news(limit=limit, topic=topic)
    print(f"Fetched {len(headlines)} headlines from Google News (Topic: {topic})")
    
    all_proposals = []
    
    analysis_count = 0
    MAX_ANALYSIS = 3

    for item in headlines:
        if analysis_count >= MAX_ANALYSIS:
            break

        analysis_count += 1
        news = NewsHeadline(
            headline=item['headline'],
            source=item['source'],
            timestamp=item['timestamp'],
            url=item['url']
        )
        
        print(f"Analyzing: {news.headline}")
        result = await analyze_news(news)
        
        if result.get('message') and "Rate Limit" in result['message']:
            print("Rate limit hit, stopping scan.")
            return {
                "scanned_count": len(headlines),
                "proposals_found": len(all_proposals),
                "headlines": headlines,
                "proposals": all_proposals,
                "error": "AI Rate Limit Exceeded. Try again later."
            }
        
        if result['proposals']:
            all_proposals.extend(result['proposals'])
    
    return {
        "scanned_count": len(headlines),
        "proposals_found": len(all_proposals),
        "headlines": headlines,
        "proposals": all_proposals
    }

@app.get("/api/proposals")
async def get_proposals():
    """Get all pending trade proposals awaiting approval."""
    return {"proposals": [p.dict() for p in pending_proposals]}

@app.post("/api/proposals/approve")
async def approve_proposal(market_id: str, approve: bool = True):
    """Approve or reject a trade proposal."""
    global pending_proposals
    
    for proposal in pending_proposals:
        if proposal.market_id == market_id:
            proposal.approved = approve
            if approve:
                result = await trading_service.execute_trade(
                    market_id=proposal.market_id,
                    direction=proposal.direction,
                    amount=proposal.bet_amount
                )
                pending_proposals.remove(proposal)
                return {
                    "message": f"Trade executed for {proposal.market_title}", 
                    "proposal": proposal.dict(),
                    "trade_result": result
                }
            else:
                pending_proposals.remove(proposal)
                return {"message": f"Trade rejected for {proposal.market_title}"}
    
    raise HTTPException(status_code=404, detail="Proposal not found")

@app.delete("/api/proposals")
async def clear_proposals():
    """Clear all pending proposals."""
    global pending_proposals
    pending_proposals = []
    return {"message": "All proposals cleared"}

@app.get("/api/positions/{wallet}")
async def get_positions(wallet: str):
    """Get user's current positions."""
    positions = get_user_positions(wallet)
    return {"positions": positions}

# ============= Wallet Endpoints (Async) =============

@app.get("/api/wallet")
async def get_wallet():
    """Get wallet status and balance."""
    if not wallet_service.is_configured():
        return {
            "configured": False,
            "message": "Set CDP_API_KEY_ID and CDP_API_KEY_SECRET env vars"
        }
    
    usdc_balance = await wallet_service.get_balance("usdc")
    eth_balance = await wallet_service.get_native_balance()
    
    return {
        "configured": True,
        "address": wallet_service.get_address(),
        "usdc_balance": usdc_balance,
        "eth_balance": eth_balance
    }

@app.get("/api/portfolio")
async def get_portfolio():
    """Get full portfolio status."""
    return trading_service.get_portfolio()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
