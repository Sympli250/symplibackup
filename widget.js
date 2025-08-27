/**
 * Initialise le widget de message d'accueil.
 * @param {Object} userConfig Configuration venant du configurateur.
 * @param {string} userConfig.message Texte du message d'accueil.
 * @param {string} userConfig.displayMode Mode d'affichage ('bubble_immediate', 'bubble_delayed', 'window_only').
 * @param {number} userConfig.delay Délai en ms pour le mode "bubble_delayed".
 * @param {string} userConfig.bubbleSelector Sélecteur CSS de la bulle de chat.
 * @param {string} userConfig.chatSelector Sélecteur CSS de la fenêtre de chat.
 */
export function initGreetingWidget(userConfig = {}) {
  const config = {
    message: 'Bonjour !',
    displayMode: 'bubble_immediate', // 'bubble_immediate', 'bubble_delayed', 'window_only'
    delay: 30000,
    bubbleSelector: '.chat-bubble',
    chatSelector: '.chat-window',
    ...userConfig
  };

  function createPopover() {
    const el = document.createElement('div');
    el.className = 'greeting-popover';
    el.textContent = config.message;
    return el;
  }

  function showBubbleGreeting() {
    const bubble = document.querySelector(config.bubbleSelector);
    if (!bubble) return;
    const pop = createPopover();
    bubble.parentNode.insertBefore(pop, bubble);
  }

  function showChatGreeting() {
    const chat = document.querySelector(config.chatSelector);
    if (!chat) return;
    const pop = createPopover();
    chat.appendChild(pop);
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (config.displayMode === 'bubble_immediate') {
      showBubbleGreeting();
    } else if (config.displayMode === 'bubble_delayed') {
      setTimeout(showBubbleGreeting, config.delay);
    } else if (config.displayMode === 'window_only') {
      const bubble = document.querySelector(config.bubbleSelector);
      if (bubble) {
        bubble.addEventListener(
          'click',
          () => {
            showChatGreeting();
          },
          { once: true }
        );
      }
    }
  });
}
