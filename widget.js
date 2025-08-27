/**
 * Initialise le widget de message d'accueil.
 * @param {Object} userConfig Configuration venant du configurateur.
 * @param {string} userConfig.message Texte du message d'accueil.
 * @param {string} userConfig.displayMode Mode d'affichage ('bubble_immediate', 'bubble_delayed', 'window_only').
 * @param {number} userConfig.delay Délai en secondes pour le mode "bubble_delayed" (défaut 30).
 * @param {string[]} userConfig.quickReplies Libellés des réponses rapides (affichées dans l'ordre fourni).
 * @param {boolean} userConfig.closable Message fermable ou non (défaut true).
 * @param {string} userConfig.bubbleSelector Sélecteur CSS de la bulle de chat.
 * @param {string} userConfig.chatSelector Sélecteur CSS de la fenêtre de chat.
 */
export function initGreetingWidget(userConfig = {}) {
  const config = {
    message: 'Bonjour !',
    displayMode: 'bubble_immediate', // 'bubble_immediate', 'bubble_delayed', 'window_only'
    delay: 30, // en secondes
    quickReplies: [],
    closable: true,
    bubbleSelector: '.chat-bubble',
    chatSelector: '.chat-window',
    ...userConfig
  };

  function createPopover() {
    const el = document.createElement('div');
    el.className = 'greeting-popover';

    const msgEl = document.createElement('div');
    msgEl.className = 'greeting-message';
    msgEl.textContent = config.message;
    el.appendChild(msgEl);

    if (config.closable) {
      const closeBtn = document.createElement('button');
      closeBtn.className = 'greeting-close';
      closeBtn.textContent = '\u00d7';
      closeBtn.addEventListener('click', () => el.remove());
      el.appendChild(closeBtn);
    }

    if (Array.isArray(config.quickReplies) && config.quickReplies.length > 0) {
      const repliesEl = document.createElement('div');
      repliesEl.className = 'greeting-quick-replies';
      config.quickReplies.forEach((label) => {
        const btn = document.createElement('button');
        btn.className = 'greeting-quick-reply';
        btn.textContent = label;
        btn.addEventListener('click', () => {
          const evt = new CustomEvent('greeting-quick-reply', { detail: { label } });
          document.dispatchEvent(evt);
          el.remove();
        });
        repliesEl.appendChild(btn);
      });
      el.appendChild(repliesEl);
    }

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
      setTimeout(showBubbleGreeting, config.delay * 1000);
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
