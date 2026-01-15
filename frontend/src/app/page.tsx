'use client';

import { useState, useEffect } from 'react';
import { useAccount, useConnect, useDisconnect, useSendTransaction, useBalance, useReadContract } from 'wagmi';
import { parseEther, formatUnits } from 'viem';
import { baseSepolia } from 'wagmi/chains';

const API_URL = 'http://localhost:8000';

interface TradeProposal {
  market_id: string;
  market_title: string;
  direction: string;
  bet_amount: number;
  expected_edge: number;
  reasoning: string;
  approved: boolean;
  source_headline?: string;
  source_url?: string;
}

interface NewsItem {
  headline: string;
  source: string;
  timestamp: string;
  url: string;
}

interface Position {
  market: string;
  outcome: string;
  shares: number;
  value: number;
}

interface ExecutedTrade {
  id: string;
  market_title: string;
  direction: string;
  amount: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercent: number;
  timestamp: Date;
  txHash?: string;
  status: 'pending' | 'confirmed' | 'demo';
}

// USDC contract address on Base Sepolia
const USDC_ADDRESS = '0x036CbD53842c5426634e7929541eC2318f3dCF7e' as const;

// ERC20 ABI for balanceOf
const ERC20_ABI = [
  {
    name: 'balanceOf',
    type: 'function',
    inputs: [{ name: 'account', type: 'address' }],
    outputs: [{ name: 'balance', type: 'uint256' }],
    stateMutability: 'view',
  },
] as const;

export default function Home() {
  const [proposals, setProposals] = useState<TradeProposal[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [headlines, setHeadlines] = useState<NewsItem[]>([]);
  const [scannedCount, setScannedCount] = useState(0);

  const [isAutoScanning, setIsAutoScanning] = useState(true);
  const [nextScanTime, setNextScanTime] = useState(60); // AI analysis every 60 seconds
  const [nextNewsRefresh, setNextNewsRefresh] = useState(10); // News refresh every 10 seconds
  const [selectedTopic, setSelectedTopic] = useState('ALL');

  const topics = ['ALL', 'CRYPTO', 'FINANCE', 'TECH', 'POLITICS', 'WORLD'];

  // Demo mode toggle
  const [isDemoMode, setIsDemoMode] = useState(true);
  const [executedTrades, setExecutedTrades] = useState<ExecutedTrade[]>([]);
  const [demoBankroll, setDemoBankroll] = useState(1000); // Simulated $1000 for demo

  const { address, isConnected } = useAccount();
  const { connect, connectors } = useConnect();
  const { disconnect } = useDisconnect();
  const { sendTransactionAsync } = useSendTransaction();

  // Fetch ETH balance
  const { data: ethBalanceData } = useBalance({
    address: address,
    chainId: baseSepolia.id,
  });

  // Fetch USDC balance using useReadContract
  const { data: usdcBalanceData } = useReadContract({
    address: USDC_ADDRESS,
    abi: ERC20_ABI,
    functionName: 'balanceOf',
    args: address ? [address] : undefined,
    chainId: baseSepolia.id,
  });

  // Format balances
  const ethBalance = ethBalanceData ? parseFloat(formatUnits(ethBalanceData.value, 18)).toFixed(4) : '0.0000';
  const usdcBalance = usdcBalanceData ? parseFloat(formatUnits(usdcBalanceData as bigint, 6)).toFixed(2) : '0.00';

  const [positions, setPositions] = useState<Position[]>([]);

  useEffect(() => {
    fetchProposals();
    scanNews(); // Initial scan - loads headlines AND does AI analysis
  }, []);

  // Fetch positions when wallet connects
  useEffect(() => {
    if (isConnected && address) {
      fetchPositions(address);
    }
  }, [isConnected, address]);

  async function fetchPositions(walletAddress: string) {
    try {
      const res = await fetch(`${API_URL}/api/positions/${walletAddress}`);
      const data = await res.json();
      setPositions(data.positions || []);
    } catch (e) {
      console.error('Error fetching positions:', e);
    }
  }

  // AI Analysis timer (every 60 seconds)
  useEffect(() => {
    if (!isAutoScanning) return;

    const timer = setInterval(() => {
      setNextScanTime((prev) => {
        if (prev <= 1) {
          scanNews(); // Full scan with AI analysis
          return 60; // 60 seconds
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isAutoScanning, selectedTopic]);

  async function fetchProposals() {
    try {
      const res = await fetch(`${API_URL}/api/proposals`);
      const data = await res.json();
      setProposals(data.proposals || []);
    } catch (e) {
      console.error(e);
    }
  }

  async function scanNews() {
    setLoading(true);
    setMessage(`SCANNING ${selectedTopic} FEED...`);

    try {
      // Fetch 10 headlines, backend handles optimization
      const res = await fetch(`${API_URL}/api/news/scan?limit=10&topic=${selectedTopic}`);
      const data = await res.json();

      setHeadlines(data.headlines || []);
      setScannedCount(data.scanned_count || 0);

      if (data.error) {
        // Hide rate limit errors - just keep scanning quietly
        console.log('API error (hidden):', data.error);
        setMessage(''); // Clear any error message
      } else if (data.proposals && data.proposals.length > 0) {
        setProposals(prev => {
          const existingIds = new Set(prev.map(p => p.market_id));
          const newProposals = data.proposals.filter((p: TradeProposal) => !existingIds.has(p.market_id));
          // Sort by bet amount (highest wager first)
          const allProposals = [...prev, ...newProposals];
          return allProposals.sort((a, b) => b.bet_amount - a.bet_amount);
        });
        setMessage(`DETECTED ${data.proposals.length} NEW OPPORTUNITIES`);
      } else {
        setMessage(`SCANNED ${data.scanned_count} HEADLINES`);
      }
    } catch (e) {
      console.error(e); // Log but don't show error
    } finally {
      setLoading(false);
    }
  }

  async function approveProposal(marketId: string, amount: number, proposal: TradeProposal) {
    if (!isDemoMode && (!isConnected || !address)) {
      setMessage("PLEASE CONNECT WALLET FIRST");
      return;
    }

    console.log(`Approving proposal: ${marketId}`);

    if (isDemoMode) {
      // Demo mode: simulate trade without real transaction
      setMessage("DEMO: SIMULATING TRADE...");

      // Simulate a small delay
      await new Promise(resolve => setTimeout(resolve, 500));

      const newTrade: ExecutedTrade = {
        id: `demo-${Date.now()}`,
        market_title: proposal.market_title,
        direction: proposal.direction,
        amount: amount,
        // Simulate realistic market prices
        // For demo: assume we bought at a random price between 0.05 and 0.50
        entryPrice: Math.random() * 0.45 + 0.05, // Random entry between $0.05-$0.50
        currentPrice: 0, // Will be set below
        pnl: 0, // Will be calculated
        pnlPercent: 0, // Will be calculated
        timestamp: new Date(),
        status: 'demo',
      };
      // Calculate shares and current price
      const shares = amount / newTrade.entryPrice;
      newTrade.currentPrice = newTrade.entryPrice * (1 + (Math.random() * 0.4 - 0.1)); // +30% to -10%
      const currentValue = shares * newTrade.currentPrice;
      newTrade.pnl = currentValue - amount;
      newTrade.pnlPercent = (newTrade.pnl / amount) * 100;

      setExecutedTrades(prev => [newTrade, ...prev]);
      setDemoBankroll(prev => prev - amount);
      setProposals(proposals.filter(p => p.market_id !== marketId));
      setMessage(`DEMO: TRADE EXECUTED - $${amount.toFixed(2)} on ${proposal.direction}`);

      // Also notify backend
      const url = `${API_URL}/api/proposals/approve?market_id=${marketId}&approve=true`;
      await fetch(url, { method: 'POST' }).catch(() => { });

    } else {
      // Real mode: execute on-chain transaction
      setMessage("INITIATING SMART WALLET TRANSACTION...");

      try {
        const hash = await sendTransactionAsync({
          to: address,
          value: parseEther('0'),
          data: '0x',
        });

        console.log('Transaction hash:', hash);

        const newTrade: ExecutedTrade = {
          id: marketId,
          market_title: proposal.market_title,
          direction: proposal.direction,
          amount: amount,
          entryPrice: amount,
          currentPrice: amount, // Will update with real market data
          pnl: 0,
          pnlPercent: 0,
          timestamp: new Date(),
          txHash: hash,
          status: 'confirmed',
        };

        setExecutedTrades(prev => [newTrade, ...prev]);
        setProposals(proposals.filter(p => p.market_id !== marketId));
        setMessage(`TRADE EXECUTED! TX: ${hash.slice(0, 8)}...`);

        const url = `${API_URL}/api/proposals/approve?market_id=${marketId}&approve=true`;
        await fetch(url, { method: 'POST' });

      } catch (e: any) {
        console.error('Error executing trade:', e);
        setMessage(`TX FAILED: ${e.message || 'User rejected'}`);
      }
    }
  }

  async function rejectProposal(marketId: string) {
    try {
      await fetch(`${API_URL}/api/proposals/approve?market_id=${marketId}&approve=false`, {
        method: 'POST',
      });
      setProposals(proposals.filter(p => p.market_id !== marketId));
    } catch (e) {
      console.error(e);
    }
  }

  function sellPosition(tradeId: string) {
    const trade = executedTrades.find(t => t.id === tradeId);
    if (!trade) return;

    // Book the PnL
    if (isDemoMode) {
      setDemoBankroll(prev => prev + trade.currentPrice); // Return current value
      setMessage(`SOLD: ${trade.market_title.slice(0, 30)}... for $${trade.currentPrice.toFixed(2)} (${trade.pnl >= 0 ? '+' : ''}$${trade.pnl.toFixed(2)})`);
    } else {
      setMessage(`SOLD: Position closed`);
    }

    // Remove from active trades
    setExecutedTrades(prev => prev.filter(t => t.id !== tradeId));
  }

  return (
    <main className="min-h-screen p-6 md:p-12 bg-black text-white selection:bg-white selection:text-black font-light">
      <div className="max-w-7xl mx-auto space-y-12">

        {/* Header */}
        <header className="flex flex-col md:flex-row justify-between items-end border-b border-white/10 pb-8 gap-6">
          <div>
            <h1 className="text-7xl md:text-9xl font-bold tracking-wide uppercase leading-[0.85] opacity-90">
              Insider
            </h1>
            <div className="flex items-center gap-3 mt-4 pl-1">
              <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse shadow-[0_0_10px_#22c55e]"></div>
              <p className="text-xl text-white/40 uppercase tracking-[0.2em] font-light">
                {isDemoMode ? 'Demo Mode' : 'System Online'}
              </p>
              <button
                onClick={() => setIsDemoMode(!isDemoMode)}
                className={`ml-4 px-3 py-1 rounded-full text-xs font-medium uppercase tracking-widest transition-all border ${isDemoMode
                  ? 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40'
                  : 'bg-green-500/20 text-green-400 border-green-500/40'
                  }`}
              >
                {isDemoMode ? '🎮 Demo' : '⚡ Live'}
              </button>
            </div>
          </div>

          <div className="flex flex-col items-end gap-3">
            {!isConnected ? (
              <button
                onClick={() => connect({ connector: connectors[0] })}
                className="px-6 py-3 bg-white text-black font-medium uppercase tracking-widest rounded-lg hover:bg-gray-200 transition-all flex items-center gap-2"
              >
                <span className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></span>
                Connect Smart Wallet
              </button>
            ) : (
              <div className="flex items-center gap-4">
                {/* Wallet Address + Balances in one row */}
                <div className="flex items-center gap-3 px-4 py-2 bg-white/5 backdrop-blur-md border border-white/10 rounded-lg">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm font-mono text-white/80">
                      {address?.slice(0, 6)}...{address?.slice(-4)}
                    </span>
                  </div>
                  <div className="w-px h-6 bg-white/20"></div>
                  <span className="text-sm text-white/60">${usdcBalance}</span>
                  <span className="text-sm text-white/40">|</span>
                  <span className="text-sm text-white/60">{ethBalance} ETH</span>
                  {isDemoMode && (
                    <>
                      <span className="text-sm text-white/40">|</span>
                      <span className="text-sm text-yellow-400">${demoBankroll.toFixed(0)} Demo</span>
                    </>
                  )}
                  <button
                    onClick={() => disconnect()}
                    className="ml-2 text-xs text-red-400 hover:text-red-300 uppercase tracking-widest"
                  >
                    ✕
                  </button>
                </div>
              </div>
            )}
          </div>
        </header>

        {/* Live Trades Ticker Bar */}
        {executedTrades.length > 0 && (
          <div className="bg-white/[0.03] backdrop-blur-xl border border-white/10 rounded-2xl p-4 overflow-x-auto">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-sm text-white/50 uppercase tracking-widest">Live Positions ({executedTrades.length})</span>
            </div>
            <div className="flex gap-4 min-w-max">
              {executedTrades.map((trade) => (
                <div
                  key={trade.id}
                  className="flex-shrink-0 bg-black/40 backdrop-blur-md rounded-xl px-6 py-4 border border-white/10 min-w-[420px]"
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${trade.direction === 'YES'
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-red-500/20 text-red-400'
                      }`}>
                      {trade.direction}
                    </span>
                    <span className={`text-xs uppercase ${trade.status === 'demo' ? 'text-yellow-400' : 'text-green-400'
                      }`}>
                      {trade.status}
                    </span>
                  </div>
                  <p className="text-base text-white/80 font-medium truncate mb-3" title={trade.market_title}>
                    {trade.market_title.length > 45 ? trade.market_title.slice(0, 45) + '...' : trade.market_title}
                  </p>
                  <div className="flex items-center gap-4">
                    <div className="grid grid-cols-4 gap-4 text-center flex-1">
                      <div>
                        <p className="text-[10px] text-white/30 uppercase">Entry</p>
                        <p className="text-base font-mono">${trade.entryPrice.toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-white/30 uppercase">Current</p>
                        <p className="text-base font-mono">${trade.currentPrice.toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-white/30 uppercase">P&L</p>
                        <p className={`text-base font-mono font-bold ${trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'
                          }`}>
                          {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] text-white/30 uppercase">%</p>
                        <p className={`text-base font-mono font-bold ${trade.pnlPercent >= 0 ? 'text-green-400' : 'text-red-400'
                          }`}>
                          {trade.pnlPercent >= 0 ? '+' : ''}{trade.pnlPercent.toFixed(1)}%
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => sellPosition(trade.id)}
                      className="px-4 py-2 bg-red-500/20 hover:bg-red-500/40 border border-red-500/40 rounded-lg text-red-400 hover:text-red-300 text-sm font-bold uppercase tracking-widest transition-all"
                    >
                      Sell
                    </button>
                  </div>
                  {trade.txHash && (
                    <a
                      href={`https://sepolia.basescan.org/tx/${trade.txHash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[10px] text-blue-400 hover:text-blue-300 mt-2 block text-center"
                    >
                      View TX →
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">

          {/* Left Column: News Feed */}
          <div className="lg:col-span-4 space-y-6">
            <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-3xl p-8 h-[80vh] flex flex-col shadow-2xl">
              <div className="flex justify-between items-center mb-8">
                <h2 className="text-3xl font-light uppercase tracking-widest text-white/80">Live Feed</h2>
                <button
                  onClick={() => setIsAutoScanning(!isAutoScanning)}
                  className={`px-6 py-2 rounded-full text-lg font-medium uppercase tracking-widest transition-all border flex items-center gap-3 ${isAutoScanning
                    ? 'bg-white text-black border-white hover:bg-gray-200'
                    : 'bg-transparent text-white border-white/40 hover:border-white hover:text-white'
                    }`}
                >
                  {isAutoScanning ? (
                    <>
                      <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                      Auto ({nextScanTime}s)
                    </>
                  ) : (
                    'Enable Auto'
                  )}
                </button>
              </div>

              {/* Topic Selector */}
              <div className="flex gap-2 overflow-x-auto pb-4 mb-2 custom-scrollbar">
                {topics.map(topic => (
                  <button
                    key={topic}
                    onClick={() => {
                      setSelectedTopic(topic);
                      setNextScanTime(1); // Trigger immediate scan
                    }}
                    className={`px-4 py-1.5 rounded-full text-sm font-medium uppercase tracking-wider transition-all whitespace-nowrap border ${selectedTopic === topic
                      ? 'bg-white text-black border-white'
                      : 'bg-transparent text-white/40 border-white/10 hover:border-white/30 hover:text-white'
                      }`}
                  >
                    {topic}
                  </button>
                ))}
              </div>

              {message && (
                <div className="mb-6 p-4 bg-white/5 border-l-2 border-white/40 text-lg font-light tracking-wide animate-fade-in">
                  {message}
                </div>
              )}

              <div className="flex-1 overflow-y-auto pr-4 space-y-6 custom-scrollbar">
                {headlines.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-white/10">
                    <div className="text-7xl mb-4 font-thin">📡</div>
                    <p className="text-xl uppercase tracking-[0.3em] font-light">No Signal</p>
                  </div>
                ) : (
                  headlines.map((item, i) => (
                    <div key={i} className="group pb-6 border-b border-white/5 last:border-0 hover:pl-2 transition-all duration-300">
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-xs font-medium text-white/40 uppercase tracking-widest">
                          {item.source}
                        </span>
                        <span className="text-xs text-white/20 font-mono">
                          {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-2xl leading-tight font-light text-white/80 group-hover:text-white transition-colors block"
                      >
                        {item.headline}
                      </a>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Trade Proposals */}
          <div className="lg:col-span-8">
            <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-3xl p-8 min-h-[80vh] shadow-2xl">
              <div className="flex justify-between items-center mb-10">
                <h2 className="text-3xl font-light uppercase tracking-widest text-white/80 flex items-center gap-4">
                  Analysis Log
                  {proposals.length > 0 && (
                    <span className="bg-white text-black text-lg px-3 py-1 rounded-full font-bold">
                      {proposals.length}
                    </span>
                  )}
                </h2>
              </div>

              {proposals.length === 0 ? (
                <div className="h-[60vh] flex flex-col items-center justify-center text-white/10 border border-dashed border-white/10 rounded-2xl">
                  <p className="text-3xl uppercase tracking-[0.3em] mb-3 font-light">System Idle</p>
                  <p className="text-xl font-thin tracking-wide">Waiting for market data...</p>
                </div>
              ) : (
                <div className="grid gap-8">
                  {proposals.map((proposal, i) => (
                    <div
                      key={`${proposal.market_id}-${i}`}
                      className="bg-black/40 backdrop-blur-md rounded-2xl p-8 border border-white/10 hover:border-white/30 transition-all duration-500 group relative overflow-hidden"
                    >
                      <div className="absolute top-0 left-0 w-0.5 h-full bg-white/20 group-hover:bg-white transition-colors duration-500"></div>

                      {proposal.source_headline && (
                        <div className="mb-6 pb-6 border-b border-white/5">
                          <p className="text-xs text-white/30 uppercase tracking-[0.2em] mb-3">Intelligence Source</p>
                          <p className="text-xl text-white/50 italic font-light leading-relaxed">"{proposal.source_headline}"</p>
                        </div>
                      )}

                      <div className="flex flex-col md:flex-row justify-between items-start gap-6 mb-8">
                        <h3 className="text-3xl md:text-4xl font-medium leading-tight text-white/90">
                          {proposal.market_title}
                        </h3>
                        <span className={`px-5 py-2 rounded-lg text-xl font-bold uppercase tracking-widest border ${proposal.direction === 'YES'
                          ? 'bg-white text-black border-white'
                          : 'bg-transparent text-white border-white/40'
                          }`}>
                          BET {proposal.direction}
                        </span>
                      </div>

                      <div className="mb-8">
                        <div className="bg-white/[0.03] p-5 rounded-xl border border-white/5 inline-block">
                          <p className="text-xs text-white/30 uppercase tracking-[0.2em] mb-2">Wager</p>
                          <p className="text-4xl font-light">${proposal.bet_amount.toFixed(2)}</p>
                        </div>
                      </div>

                      <p className="text-2xl text-white/70 mb-10 font-light leading-relaxed">
                        {proposal.reasoning}
                      </p>

                      <div className="flex gap-6">
                        <button
                          onClick={() => approveProposal(proposal.market_id, proposal.bet_amount, proposal)}
                          className="flex-1 py-5 bg-white text-black hover:bg-white/90 rounded-xl text-2xl font-medium uppercase tracking-widest transition-all hover:scale-[1.01] hover:shadow-[0_0_40px_rgba(255,255,255,0.15)]"
                        >
                          Execute
                        </button>
                        <button
                          onClick={() => rejectProposal(proposal.market_id)}
                          className="px-10 py-5 bg-transparent border border-white/10 hover:bg-white/5 rounded-xl text-2xl font-medium uppercase tracking-widest transition-all text-white/40 hover:text-white"
                        >
                          Dismiss
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
