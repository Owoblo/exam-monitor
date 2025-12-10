// Content script that runs on all pages to monitor clipboard and paste activity

// List of AI sites where we want to monitor paste activity
const AI_SITES = [
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

// Check if we're on an AI site
const currentDomain = window.location.hostname.replace('www.', '');
const isAISite = AI_SITES.some(site => currentDomain.includes(site));

if (isAISite) {
  console.log('🔒 Exam Monitor: Clipboard monitoring active on', currentDomain);

  // Monitor paste events
  document.addEventListener('paste', function(e) {
    // Get pasted text
    const pastedText = (e.clipboardData || window.clipboardData).getData('text');

    if (pastedText && pastedText.length > 10) {
      console.log('📋 PASTE DETECTED on AI site!');

      // Send paste event to background script
      chrome.runtime.sendMessage({
        type: 'PASTE_DETECTED',
        domain: currentDomain,
        pastedText: pastedText.substring(0, 500), // First 500 chars
        textLength: pastedText.length,
        timestamp: new Date().toISOString(),
        url: window.location.href
      });
    }
  }, true);

  // Monitor copy events (what they're copying FROM ChatGPT)
  document.addEventListener('copy', function(e) {
    const selectedText = window.getSelection().toString();

    if (selectedText && selectedText.length > 10) {
      console.log('📄 COPY DETECTED from AI site!');

      // Send copy event to background script
      chrome.runtime.sendMessage({
        type: 'COPY_DETECTED',
        domain: currentDomain,
        copiedText: selectedText.substring(0, 500), // First 500 chars
        textLength: selectedText.length,
        timestamp: new Date().toISOString(),
        url: window.location.href
      });
    }
  }, true);

  // Monitor keyboard input on AI sites
  let typingTimeout;
  let typedContent = '';

  document.addEventListener('keydown', function(e) {
    // Track when user is typing in input fields
    if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT' || e.target.isContentEditable) {
      clearTimeout(typingTimeout);

      // Wait 2 seconds after they stop typing
      typingTimeout = setTimeout(() => {
        const content = e.target.value || e.target.textContent;

        if (content && content.length > 20 && content !== typedContent) {
          typedContent = content;
          console.log('⌨️ TYPING DETECTED in AI site input!');

          chrome.runtime.sendMessage({
            type: 'TYPING_DETECTED',
            domain: currentDomain,
            inputText: content.substring(0, 500),
            textLength: content.length,
            timestamp: new Date().toISOString(),
            url: window.location.href
          });
        }
      }, 2000);
    }
  }, true);
}

// Listen for messages from background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'getPageContent') {
    // Send back the page content if requested
    sendResponse({
      content: document.body.innerText.substring(0, 1000),
      url: window.location.href
    });
  }
});
