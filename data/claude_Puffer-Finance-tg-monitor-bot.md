# Multi-Token Ethereum Monitor Bot Implementation Agent

## Purpose Statement
This agent facilitates the implementation and deployment of a real-time Ethereum token monitoring system with Telegram notification capabilities. The system monitors ERC-20 token deposits across specified contracts and provides configurable operational modes.

## System Architecture Overview

### Core Components
1. **Ethereum Blockchain Interface**: Etherscan API integration for transaction monitoring
2. **Notification System**: Telegram bot for real-time alerts
3. **Token Registry**: Multi-token support with extensible configuration
4. **Operational Modes**: Full monitoring and analysis-only capabilities

### Supported Token Contracts
```
CARROT: 0x48e8dE138C246c14248C94d2D616a2F9eb4590D2
PUFFER: 0x4d1c297d39c5c1277964d0e3f8aa901493664530
pufETH: 0xd9a442856c234a39a81a089c06451ebaa4306a72
```

## Implementation Protocol

### Phase 1: Environment Preparation

#### 1.1 Repository Initialization
```bash
# Create project directory
mkdir eth-monitor-bot && cd eth-monitor-bot

# Initialize npm project
npm init -y

# Create directory structure
mkdir -p src tests logs
```

#### 1.2 Dependency Installation
```bash
# Production dependencies
npm install axios node-telegram-bot-api dotenv

# Development dependencies
npm install --save-dev nodemon jest @types/node
```

#### 1.3 Environment Configuration
Create `.env` file with the following structure:
```env
# API Credentials
ETHERSCAN_API_KEY=<obtain_from_etherscan.io/myapikey>
TELEGRAM_BOT_TOKEN=<obtain_from_telegram_botfather>
CHAT_ID=<your_telegram_chat_id>

# Token Contract Addresses
CARROT_TOKEN_ADDRESS=0x48e8dE138C246c14248C94d2D616a2F9eb4590D2
PUFFER_TOKEN_ADDRESS=0x4d1c297d39c5c1277964d0e3f8aa901493664530
PUFETH_TOKEN_ADDRESS=0xd9a442856c234a39a81a089c06451ebaa4306a72

# Operational Parameters
POLLING_INTERVAL=60000
MAX_RETRIES=3
RETRY_DELAY=5000
```

### Phase 2: Core Implementation

#### 2.1 Token Configuration Module
Create `src/tokens.js`:
```javascript
module.exports = {
  TOKENS: [
    {
      address: process.env.CARROT_TOKEN_ADDRESS,
      symbol: 'CARROT',
      name: 'CARROT Token',
      emoji: '🥕',
      decimals: 18
    },
    {
      address: process.env.PUFFER_TOKEN_ADDRESS,
      symbol: 'PUFFER',
      name: 'Puffer Finance Token',
      emoji: '🐡',
      decimals: 18
    },
    {
      address: process.env.PUFETH_TOKEN_ADDRESS,
      symbol: 'pufETH',
      name: 'Puffer ETH',
      emoji: '💎',
      decimals: 18
    }
  ]
};
```

#### 2.2 Etherscan Integration Module
Create `src/etherscan.js`:
```javascript
const axios = require('axios');

class EtherscanClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.baseUrl = 'https://api.etherscan.io/api';
    this.processedTransactions = new Set();
  }

  async getTokenTransfers(tokenAddress, targetAddress, startBlock = 0) {
    const params = {
      module: 'account',
      action: 'tokentx',
      contractaddress: tokenAddress,
      address: targetAddress,
      startblock: startBlock,
      endblock: 'latest',
      sort: 'desc',
      apikey: this.apiKey
    };

    try {
      const response = await axios.get(this.baseUrl, { params });
      return response.data.result || [];
    } catch (error) {
      throw new Error(`Etherscan API error: ${error.message}`);
    }
  }

  isNewTransaction(txHash) {
    if (this.processedTransactions.has(txHash)) {
      return false;
    }
    this.processedTransactions.add(txHash);
    return true;
  }
}

module.exports = EtherscanClient;
```

#### 2.3 Telegram Notification Module
Create `src/telegram.js`:
```javascript
const TelegramBot = require('node-telegram-bot-api');

class TelegramNotifier {
  constructor(token, chatId) {
    this.bot = new TelegramBot(token, { polling: true });
    this.chatId = chatId;
    this.setupCommands();
  }

  setupCommands() {
    this.bot.onText(/\/status/, (msg) => {
      this.sendStatus();
    });

    this.bot.onText(/\/tokens/, (msg) => {
      this.sendTokenList();
    });

    this.bot.onText(/\/help/, (msg) => {
      this.sendHelp();
    });
  }

  async sendDepositAlert(tokenInfo, transaction) {
    const message = `
${tokenInfo.emoji} ${tokenInfo.symbol} DEPOSIT ALERT ${tokenInfo.emoji}

Amount: ${this.formatAmount(transaction.value, tokenInfo.decimals)} ${tokenInfo.symbol}
From: ${transaction.from}
To: ${transaction.to}
Transaction: https://etherscan.io/tx/${transaction.hash}
Block: ${transaction.blockNumber}
Timestamp: ${new Date(transaction.timeStamp * 1000).toLocaleString()}
`;
    
    await this.bot.sendMessage(this.chatId, message);
  }

  formatAmount(value, decimals) {
    return (value / Math.pow(10, decimals)).toFixed(6);
  }
}

module.exports = TelegramNotifier;
```

#### 2.4 Main Application Module
Create `src/index.js`:
```javascript
require('dotenv').config();
const EtherscanClient = require('./etherscan');
const TelegramNotifier = require('./telegram');
const { TOKENS } = require('./tokens');

class TokenMonitor {
  constructor(mode = 'full') {
    this.mode = mode;
    this.etherscan = new EtherscanClient(process.env.ETHERSCAN_API_KEY);
    this.telegram = new TelegramNotifier(
      process.env.TELEGRAM_BOT_TOKEN,
      process.env.CHAT_ID
    );
    this.pollingInterval = parseInt(process.env.POLLING_INTERVAL) || 60000;
    this.isRunning = false;
  }

  async start() {
    if (this.mode === 'full') {
      console.log('Starting token monitor in FULL mode...');
      await this.telegram.bot.sendMessage(
        this.telegram.chatId,
        '🤖 Token Monitor Bot Started'
      );
      this.isRunning = true;
      this.monitorLoop();
    } else {
      console.log('Token monitor started in ANALYSIS mode');
    }
  }

  async monitorLoop() {
    while (this.isRunning) {
      await this.checkAllTokens();
      await this.sleep(this.pollingInterval);
    }
  }

  async checkAllTokens() {
    const checks = TOKENS.map(token => this.checkToken(token));
    await Promise.all(checks);
  }

  async checkToken(tokenInfo) {
    try {
      const transfers = await this.etherscan.getTokenTransfers(
        tokenInfo.address,
        tokenInfo.address
      );

      for (const tx of transfers) {
        if (tx.to.toLowerCase() === tokenInfo.address.toLowerCase() &&
            this.etherscan.isNewTransaction(tx.hash)) {
          await this.telegram.sendDepositAlert(tokenInfo, tx);
        }
      }
    } catch (error) {
      console.error(`Error checking ${tokenInfo.symbol}:`, error.message);
    }
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  stop() {
    this.isRunning = false;
    console.log('Token monitor stopped');
  }
}

// Initialize and start
const mode = process.env.NODE_ENV === 'analysis' ? 'analysis' : 'full';
const monitor = new TokenMonitor(mode);
monitor.start();

// Graceful shutdown
process.on('SIGINT', () => {
  monitor.stop();
  process.exit(0);
});
```

### Phase 3: Package Configuration

#### 3.1 Update package.json
```json
{
  "name": "eth-monitor-bot",
  "version": "1.0.0",
  "description": "Multi-token Ethereum deposit monitoring bot",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js",
    "start:analysis": "NODE_ENV=analysis node src/index.js",
    "dev": "nodemon src/index.js",
    "test": "jest",
    "test:watch": "jest --watch"
  },
  "keywords": ["ethereum", "monitoring", "telegram", "bot"],
  "author": "",
  "license": "MIT"
}
```

### Phase 4: Validation Protocol

#### 4.1 API Connectivity Verification
Create `tests/connectivity.test.js`:
```javascript
const axios = require('axios');
require('dotenv').config();

describe('API Connectivity Tests', () => {
  test('Etherscan API responds correctly', async () => {
    const response = await axios.get('https://api.etherscan.io/api', {
      params: {
        module: 'stats',
        action: 'ethsupply',
        apikey: process.env.ETHERSCAN_API_KEY
      }
    });
    expect(response.data.status).toBe('1');
  });

  test('Telegram bot token is valid', async () => {
    const response = await axios.get(
      `https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}/getMe`
    );
    expect(response.data.ok).toBe(true);
  });
});
```

#### 4.2 Token Contract Verification
```javascript
async function verifyTokenContracts() {
  const { TOKENS } = require('./src/tokens');
  
  for (const token of TOKENS) {
    console.log(`Verifying ${token.symbol} at ${token.address}...`);
    
    // Verify contract exists
    const response = await axios.get('https://api.etherscan.io/api', {
      params: {
        module: 'proxy',
        action: 'eth_getCode',
        address: token.address,
        apikey: process.env.ETHERSCAN_API_KEY
      }
    });
    
    if (response.data.result === '0x') {
      console.error(`ERROR: ${token.symbol} contract not found`);
    } else {
      console.log(`✓ ${token.symbol} contract verified`);
    }
  }
}
```

### Phase 5: Error Handling Implementation

#### 5.1 Rate Limiting Handler
```javascript
class RateLimiter {
  constructor(maxRetries = 3, retryDelay = 5000) {
    this.maxRetries = maxRetries;
    this.retryDelay = retryDelay;
  }

  async executeWithRetry(fn, context = null) {
    let lastError;
    
    for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
      try {
        return await fn.call(context);
      } catch (error) {
        lastError = error;
        
        if (error.response?.status === 429) {
          console.log(`Rate limit hit, waiting ${this.retryDelay}ms...`);
          await this.sleep(this.retryDelay * attempt);
        } else {
          throw error;
        }
      }
    }
    
    throw lastError;
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
```

#### 5.2 Connection Recovery
```javascript
class ConnectionManager {
  constructor() {
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
  }

  async handleConnectionError(error, service) {
    console.error(`Connection error for ${service}:`, error.message);
    
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
      console.log(`Reconnecting in ${delay}ms... (attempt ${this.reconnectAttempts})`);
      await this.sleep(delay);
      return true; // Signal to retry
    }
    
    return false; // Max attempts reached
  }

  resetReconnectCounter() {
    this.reconnectAttempts = 0;
  }
}
```

### Phase 6: Deployment Checklist

#### 6.1 Pre-deployment Verification
- [ ] All environment variables configured
- [ ] API keys validated and functional
- [ ] Token contracts verified on mainnet
- [ ] Telegram bot permissions confirmed
- [ ] Error handling tested with simulated failures
- [ ] Rate limiting tested under load

#### 6.2 Production Deployment Steps
1. **Environment Setup**
   ```bash
   # Production server
   git clone <repository>
   cd eth-monitor-bot
   npm install --production
   cp .env.example .env
   # Edit .env with production values
   ```

2. **Process Management**
   ```bash
   # Install PM2
   npm install -g pm2
   
   # Start with PM2
   pm2 start src/index.js --name "eth-monitor"
   pm2 save
   pm2 startup
   ```

3. **Monitoring Setup**
   ```bash
   # Enable PM2 monitoring
   pm2 install pm2-logrotate
   pm2 set pm2-logrotate:max_size 10M
   pm2 set pm2-logrotate:retain 7
   ```

### Phase 7: Maintenance Protocol

#### 7.1 Regular Maintenance Tasks
- **Daily**: Check error logs for API failures
- **Weekly**: Verify all monitored tokens are active
- **Monthly**: Review and optimize polling intervals
- **Quarterly**: Update dependencies and security patches

#### 7.2 Troubleshooting Guide
| Issue | Diagnostic Steps | Resolution |
|-------|-----------------|------------|
| No alerts received | Check bot status via `/status` | Verify API keys and permissions |
| Duplicate alerts | Review transaction hash tracking | Clear processed transaction cache |
| API rate limits | Monitor request frequency | Implement request queuing |
| Connection drops | Check network logs | Implement exponential backoff |

### Phase 8: Extension Guidelines

#### 8.1 Adding New Tokens
1. Add token configuration to `src/tokens.js`
2. Add environment variable to `.env`
3. Verify contract address on Etherscan
4. Test with small transaction
5. Deploy and monitor for 24 hours

#### 8.2 Feature Enhancements
- **Outbound monitoring**: Modify `checkToken()` to include `from` address filtering
- **Threshold alerts**: Add `minAmount` property to token configuration
- **Multi-address support**: Convert target address to array in token config
- **Database integration**: Implement transaction history storage

## Success Criteria
- Bot successfully starts and connects to Telegram
- All configured tokens are monitored without errors
- Incoming deposits trigger notifications within 60 seconds
- System handles API failures gracefully
- No duplicate notifications for same transaction

## Security Considerations
- Store all sensitive data in environment variables
- Never expose private keys or API tokens in logs
- Implement request signing for API calls if available
- Regular security audits of dependencies
- Monitor for unusual transaction patterns
