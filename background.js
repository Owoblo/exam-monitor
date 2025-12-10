// List of blocked AI sites
const BLOCKED_DOMAINS = [
  'chatgpt.com',
  'chat.openai.com',
  'claude.ai',
  'gemini.google.com',
  'copilot.microsoft.com',
  'bard.google.com',
  'perplexity.ai',
  'you.com',
  'poe.com',
  'character.ai'
];

// Server endpoint (your backend)
const SERVER_URL = 'http://localhost:5001/flag';

// Student ID (in real deployment, this comes from school login)
let STUDENT_ID = 'DEMO-12345';

// Monitor tab changes
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  checkCurrentTab(activeInfo.tabId);
});

// Monitor URL changes
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.url) {
    checkCurrentTab(tabId);
  }
});

async function checkCurrentTab(tabId) {
  try {
    const tab = await chrome.tabs.get(tabId);

    // Skip chrome:// and other system URLs
    if (!tab.url || tab.url.startsWith('chrome://') || tab.url.startsWith('edge://')) {
      return;
    }

    const url = new URL(tab.url);
    const hostname = url.hostname.replace('www.', '');

    // Check if current site is blocked
    const isBlocked = BLOCKED_DOMAINS.some(domain => hostname.includes(domain));

    if (isBlocked) {
      // Capture screenshot
      const screenshot = await chrome.tabs.captureVisibleTab(null, {
        format: 'png',
        quality: 80
      });

      // Send flag to server
      sendFlag(hostname, tab.url, screenshot);

      // Log locally
      console.log(`🚨 FLAGGED: ${hostname} at ${new Date().toLocaleTimeString()}`);
    }
  } catch (error) {
    console.error('Monitoring error:', error);
  }
}

async function sendFlag(domain, fullUrl, screenshot) {
  const flagData = {
    studentId: STUDENT_ID,
    domain: domain,
    fullUrl: fullUrl,
    timestamp: new Date().toISOString(),
    screenshot: screenshot
  };

  try {
    const response = await fetch(SERVER_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(flagData)
    });

    if (response.ok) {
      console.log('✅ Flag sent successfully');
    }
  } catch (error) {
    console.error('Failed to send flag:', error);
    // Store locally if server unavailable
    chrome.storage.local.get(['pendingFlags'], (result) => {
      const pending = result.pendingFlags || [];
      pending.push(flagData);
      chrome.storage.local.set({ pendingFlags: pending });
      console.log('💾 Stored flag locally (server unavailable)');
    });
  }
}

// Listen for messages from content script (paste/copy detection)
chrome.runtime.onMessage.addListener(async (message, sender, sendResponse) => {
  if (message.type === 'PASTE_DETECTED') {
    console.log('📋 PASTE DETECTED:', message.domain);

    // Capture screenshot immediately
    try {
      const screenshot = await chrome.tabs.captureVisibleTab(null, {
        format: 'png',
        quality: 80
      });

      // Send enhanced flag with paste data
      sendEnhancedFlag({
        ...message,
        flagType: 'PASTE',
        screenshot: screenshot
      });
    } catch (error) {
      console.error('Failed to capture screenshot:', error);
    }
  } else if (message.type === 'COPY_DETECTED') {
    console.log('📄 COPY DETECTED:', message.domain);

    try {
      const screenshot = await chrome.tabs.captureVisibleTab(null, {
        format: 'png',
        quality: 80
      });

      sendEnhancedFlag({
        ...message,
        flagType: 'COPY',
        screenshot: screenshot
      });
    } catch (error) {
      console.error('Failed to capture screenshot:', error);
    }
  } else if (message.type === 'TYPING_DETECTED') {
    console.log('⌨️ TYPING DETECTED:', message.domain);

    try {
      const screenshot = await chrome.tabs.captureVisibleTab(null, {
        format: 'png',
        quality: 80
      });

      sendEnhancedFlag({
        ...message,
        flagType: 'TYPING',
        screenshot: screenshot
      });
    } catch (error) {
      console.error('Failed to capture screenshot:', error);
    }
  }
});

async function sendEnhancedFlag(data) {
  const flagData = {
    studentId: STUDENT_ID,
    domain: data.domain,
    fullUrl: data.url,
    flagType: data.flagType,
    timestamp: data.timestamp,
    screenshot: data.screenshot,
    // Evidence data
    pastedText: data.pastedText || null,
    copiedText: data.copiedText || null,
    typedText: data.inputText || null,
    textLength: data.textLength || 0
  };

  try {
    const response = await fetch(SERVER_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(flagData)
    });

    if (response.ok) {
      console.log('✅ Enhanced flag sent successfully');
    }
  } catch (error) {
    console.error('Failed to send flag:', error);
    chrome.storage.local.get(['pendingFlags'], (result) => {
      const pending = result.pendingFlags || [];
      pending.push(flagData);
      chrome.storage.local.set({ pendingFlags: pending });
      console.log('💾 Stored flag locally (server unavailable)');
    });
  }
}

// Periodic screenshot capture for live monitoring
let liveMonitoringInterval = null;

function startLiveMonitoring() {
  // Capture and send screenshot every 5 seconds
  liveMonitoringInterval = setInterval(async () => {
    try {
      const tabs = await chrome.tabs.query({active: true, currentWindow: true});
      if (tabs.length > 0 && tabs[0].url && !tabs[0].url.startsWith('chrome://')) {
        const screenshot = await chrome.tabs.captureVisibleTab(null, {
          format: 'png',
          quality: 60  // Lower quality for live streaming
        });

        // Send live screenshot update
        const liveUpdate = {
          studentId: STUDENT_ID,
          screenshot: screenshot,
          currentUrl: tabs[0].url,
          currentTitle: tabs[0].title,
          timestamp: new Date().toISOString(),
          type: 'LIVE_UPDATE'
        };

        await fetch(SERVER_URL.replace('/flag', '/live-update'), {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(liveUpdate)
        });
      }
    } catch (error) {
      console.error('Live monitoring error:', error);
    }
  }, 5000); // Every 5 seconds

  console.log('📹 Live monitoring started');
}

// Listen for extension installation
chrome.runtime.onInstalled.addListener(() => {
  console.log('🔒 Exam Integrity Monitor installed and active');

  // Start live monitoring
  startLiveMonitoring();
});

// Start live monitoring when extension loads
startLiveMonitoring();
