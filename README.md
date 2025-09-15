# Poly-Maker

A market making bot for Polymarket prediction markets. This bot automates the process of providing liquidity to markets on Polymarket by maintaining orders on both sides of the book with configurable parameters. A summary of my experience running this bot is available [here](https://x.com/defiance_cr/status/1906774862254800934)

## Overview

Poly-Maker is a comprehensive solution for automated market making on Polymarket. It includes:

- Real-time order book monitoring via WebSockets
- Position management with risk controls
- Customizable trade parameters fetched from Google Sheets
- Automated position merging functionality
- Sophisticated spread and price management

## Architecture

### System Overview

Poly-Maker operates as a multi-threaded, event-driven system that continuously monitors Polymarket and executes trades based on real-time market data and configurable parameters.

### Core Components

#### 1. Main Controller (`main.py`)

- **Purpose**: Application entry point and orchestration
- **Responsibilities**:
  - Initialize the Polymarket client
  - Start background update threads
  - Manage WebSocket connections
  - Handle application lifecycle

#### 2. Polymarket Client (`poly_data/polymarket_client.py`)

- **Purpose**: Interface with Polymarket API and blockchain
- **Key Features**:
  - Order creation and management
  - Balance and position queries
  - Order book data retrieval
  - Position merging via smart contracts
- **Dependencies**: Web3, py-clob-client, Polygon RPC

#### 3. WebSocket Handlers (`poly_data/websocket_handlers.py`)

- **Purpose**: Real-time data streaming from Polymarket
- **Two Connections**:
  - **Market WebSocket**: Order book updates, price changes
  - **User WebSocket**: Personal order/trade updates
- **Features**: Auto-reconnection, error handling, data processing

#### 4. Global State Management (`poly_data/global_state.py`)

- **Purpose**: Centralized state storage for thread-safe operations
- **Key Data Structures**:
  - `all_data`: Real-time order book data
  - `positions`: Current market positions
  - `orders`: Active orders
  - `performing`: Trades in progress
  - `params`: Trading parameters from Google Sheets

#### 5. Data Processing (`poly_data/data_processing.py`)

- **Purpose**: Process incoming WebSocket data and trigger trading
- **Key Functions**:
  - `process_data()`: Handle market updates
  - `process_user_data()`: Handle user-specific events
  - Trade state management (MATCHED → CONFIRMED → MINED)

#### 6. Trading Logic (`trading.py`)

- **Purpose**: Core market making algorithm
- **Strategy**:
  - Maintain bid/ask spreads around fair value
  - Progressive position building up to max_size
  - Risk management through position limits
  - Dynamic pricing based on order book depth

## Workflow

### System Startup Process

1. **Environment Initialization**

   - Load environment variables (private keys, API credentials)
   - Initialize Polymarket client with Web3 connection
   - Set up Google Sheets API credentials

2. **Data Synchronization**

   - Fetch market data from Google Sheets ("Selected Markets" worksheet)
   - Retrieve current positions from Polymarket API
   - Load active orders from Polymarket API
   - Initialize global state with fetched data

3. **WebSocket Connection Setup**

   - Establish market WebSocket connection for order book updates
   - Establish user WebSocket connection for personal trade updates
   - Subscribe to relevant market tokens

4. **Background Thread Launch**
   - Start periodic update thread (5-second intervals)
   - Begin real-time data processing

### Real-Time Data Processing

#### Market Data Flow

1. **WebSocket Reception**: Receive order book updates from Polymarket
2. **Data Parsing**: Extract bid/ask prices and sizes
3. **State Update**: Update global order book data structures
4. **Trading Trigger**: Asynchronously trigger trading logic for affected markets

#### User Data Flow

1. **Trade Events**: Receive personal trade confirmations
2. **Status Tracking**: Monitor trade lifecycle (MATCHED → CONFIRMED → MINED)
3. **Position Updates**: Update internal position tracking
4. **Risk Management**: Implement position limits and exposure controls

### Market Making Strategy

#### Position Management

- **Progressive Building**: Start with small orders, increase size as position grows
- **Risk Limits**: Maximum position size per market (configurable via Google Sheets)
- **Exposure Control**: Total exposure across all markets
- **Dynamic Sizing**: Adjust order sizes based on market volatility and liquidity

### Error Handling & Recovery

#### WebSocket Reconnection

- Automatic reconnection on connection loss
- Exponential backoff for failed connections
- State preservation during reconnection

#### Trade Failure Handling

- Retry logic for failed orders
- Position reconciliation after failures
- Stale trade cleanup (15-second timeout)

#### Data Consistency

- Periodic position synchronization with API
- Order book validation
- Cross-reference between WebSocket and API data

### Performance Optimization

#### Memory Management

- Garbage collection after each update cycle
- Efficient data structures (SortedDict for order books)
- Minimal data copying

#### Threading Strategy

- Main thread: WebSocket management
- Background thread: Periodic data updates
- Async tasks: Individual trade processing

#### Network Efficiency

- Batch WebSocket subscriptions
- Minimal API calls through caching
- Connection pooling for HTTP requests

## Structure

The repository consists of several interconnected modules:

- `poly_data`: Core data management and market making logic
- `poly_merger`: Utility for merging positions (based on open-source Polymarket code)
- `poly_stats`: Account statistics tracking
- `poly_utils`: Shared utility functions
- `data_updater`: Separate module for collecting market information

## Requirements

- Python 3.9 with latest setuptools
- Node.js (for poly_merger)
- Google Sheets API credentials
- Polymarket account and API credentials

## Installation

Start a new virtual environment:

```
uv venv
uv pip install -r requirements.txt
uv run python update_markets.py
```

1. **Clone the repository**:

```
git clone https://github.com/yourusername/poly-maker.git
cd poly-maker
```

2. **Install Python dependencies**:

```
pip install -r requirements.txt
```

3. **Install Node.js dependencies for the merger**:

```
cd poly_merger
npm install
cd ..
```

4. **Set up environment variables**:

```
cp .env.example .env
```

5. **Configure your credentials in `.env`**:

- `PK`: Your private key for Polymarket
- `BROWSER_ADDRESS`: Your wallet address

Make sure your wallet has done at least one trade thru the UI so that the permissions are proper.

6. **Set up Google Sheets integration**:

   - Create a Google Service Account and download credentials to the main directory
   - Copy the [sample Google Sheet](https://docs.google.com/spreadsheets/d/1Kt6yGY7CZpB75cLJJAdWo7LSp9Oz7pjqfuVWwgtn7Ns/edit?gid=1884499063#gid=1884499063)
   - Add your Google service account to the sheet with edit permissions
   - Update `SPREADSHEET_URL` in your `.env` file

7. **Update market data**:

   - Run `python update_markets.py` to fetch all available markets
   - This should run continuously in the background (preferably on a different IP than your trading bot)
   - Add markets you want to trade to the "Selected Markets" sheet. You'd wanna select markets from the "Volatility Markets" sheet.
   - Configure corresponding parameters in the "Hyperparameters" sheet. Default parameters that worked well in November are there.

8. **Start the market making bot**:

```
python main.py
```

## Configuration

The bot is configured via a Google Spreadsheet with several worksheets:

- **Selected Markets**: Markets you want to trade
- **All Markets**: Database of all markets on Polymarket
- **Hyperparameters**: Configuration parameters for the trading logic

## Poly Merger

The `poly_merger` module is a particularly powerful utility that handles position merging on Polymarket. It's built on open-source Polymarket code and provides a smooth way to consolidate positions, reducing gas fees and improving capital efficiency.

## Operational Considerations

### Risk Management

- **Position Limits**: Maximum position size per market (configurable)
- **Exposure Control**: Total exposure across all markets
- **Stop Loss**: Automatic position reduction on adverse moves
- **Capital Allocation**: Never risk more than you can afford to lose

### Monitoring & Maintenance

- **Log Monitoring**: Watch for WebSocket disconnections and trade failures
- **Position Reconciliation**: Regular checks against Polymarket API
- **Performance Metrics**: Track P&L, trade frequency, and slippage
- **System Health**: Monitor memory usage and thread performance

### Deployment Best Practices

- **Separate IPs**: Run `data_updater` on different IP than trading bot
- **Redundancy**: Consider running multiple instances for critical markets
- **Backup**: Regular backups of Google Sheets configuration
- **Updates**: Test parameter changes in staging environment first

### Troubleshooting Common Issues

**WebSocket Disconnections:**

```bash
# Check network connectivity
ping clob.polymarket.com
```

### Performance Tuning

**Memory Optimization:**

- Adjust garbage collection frequency in `main.py`
- Monitor memory usage with `htop` or similar tools
- Consider reducing WebSocket subscription scope for large portfolios

**Network Optimization:**

- Use dedicated VPS with low latency to Polymarket servers
- Consider running in same region as Polymarket infrastructure
- Monitor bandwidth usage for WebSocket connections

**Trading Optimization:**

- Fine-tune parameters based on market volatility
- Adjust update frequencies based on market activity
- Consider market-specific parameter sets

## Important Notes

- This code interacts with real markets and can potentially lose real money
- Test thoroughly with small amounts before deploying with significant capital
- The `data_updater` is technically a separate repository but is included here for convenience
- Always maintain proper risk management and position limits
- Monitor system performance and adjust parameters as needed
- Keep backups of all configuration data

## License

MIT
