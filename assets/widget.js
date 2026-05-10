(function() {
    const CHATBOT_BASE = "https://chatbot.svsu.ac.in";
    const WIDGET_VERSION = "20260510-resize-compact-v1";
    const CHATBOT_IFRAME_URL = CHATBOT_BASE + "/admin_panel/chatbot.html?widget=1&v=" + encodeURIComponent(WIDGET_VERSION);
    const CHATBOT_ORIGIN = new URL(CHATBOT_BASE).origin;
    const ID = 'svsu-chatbot-v7';
    
    if (document.getElementById(ID)) return;

    const style = document.createElement('style');
    style.innerHTML = `
        #${ID}-container {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 2147483647;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            pointer-events: none;
        }
        #${ID}-launcher {
            width: 120px;
            height: 120px;
            cursor: pointer;
            position: relative;
            pointer-events: auto;
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        #${ID}-launcher:hover { transform: scale(1.08); }
        #${ID}-launcher video, #${ID}-launcher img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            filter: drop-shadow(0 10px 20px rgba(0,0,0,0.15));
        }
        #${ID}-bubble {
            position: absolute;
            bottom: 70px;
            right: 95px;
            width: 110px;
            height: 90px;
            background: url('${CHATBOT_BASE}/assets/textcloud_clean.png') center / contain no-repeat;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 10px 10px 20px 10px;
            text-align: center;
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 11px;
            font-weight: 800;
            color: #333;
            line-height: 1.2;
            cursor: pointer;
            pointer-events: auto;
            opacity: 0;
            transform: scale(0.2);
            transform-origin: bottom right;
            transition: transform 0.38s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.28s ease;
            filter: drop-shadow(0 8px 14px rgba(0, 0, 0, 0.16));
        }
        #${ID}-bubble.open {
            opacity: 1;
            transform: scale(1);
        }
        #${ID}-bubble-text {
            display: block;
            color: #333;
            text-shadow: 0 1px 0 rgba(255,255,255,0.45);
            transition: opacity 0.2s ease;
        }
        #${ID}-bubble-text.fading {
            opacity: 0;
        }
        #${ID}-frame {
            position: fixed;
            bottom: 20px !important;
            right: 20px !important;
            width: 370px !important;
            height: 630px !important;
            border: none !important;
            display: none;
            z-index: 2147483647;
            background: transparent !important;
            overflow: visible !important;
        }
        #${ID}-frame.active {
            display: block;
            animation: widgetSlideUp 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        @keyframes widgetSlideUp {
            from { opacity: 0; transform: translateY(40px) scale(0.95); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @media (max-width: 480px) {
            #${ID}-frame.active {
                width: 100% !important;
                height: 100% !important;
                bottom: 0 !important;
                right: 0 !important;
                left: 0 !important;
                top: 0 !important;
            }
        }
    `;
    document.head.appendChild(style);

    const container = document.createElement('div');
    container.id = `${ID}-container`;
    
    const bubble = document.createElement('div');
    bubble.id = `${ID}-bubble`;
    const bubbleTextId = `${ID}-bubble-text`;
    bubble.innerHTML = `<span id="${bubbleTextId}">Ask me anything about SVSU!</span>`;
    
    const launcher = document.createElement('div');
    launcher.id = `${ID}-launcher`;
    launcher.innerHTML = `<video autoplay muted loop playsinline><source src="${CHATBOT_BASE}/assets/svsugirl.webm" type="video/webm"><img src="${CHATBOT_BASE}/assets/svsugirl.png"></video>`;
    
    container.appendChild(bubble);
    container.appendChild(launcher);
    document.body.appendChild(container);

    const iframe = document.createElement('iframe');
    iframe.id = `${ID}-frame`;
    iframe.src = CHATBOT_IFRAME_URL;
    iframe.allow = "microphone; autoplay";
    iframe.setAttribute('allowtransparency', 'true');
    document.body.appendChild(iframe);

    const bubbleText = document.getElementById(bubbleTextId);
    const bubbleMessages = [
        "Ask me anything about SVSU!",
        "Need help with admissions?",
        "Explore courses, fees and campus info!",
        "Tap here and chat with SVSU Guide!"
    ];
    const BUBBLE_OPEN_MS = 2200;
    const BUBBLE_CLOSED_MS = 1600;
    let bubbleIndex = 0;
    let bubbleTimer = null;
    let bubbleCycleToken = 0;

    function clearBubbleTimer() {
        if (bubbleTimer) {
            clearTimeout(bubbleTimer);
            bubbleTimer = null;
        }
    }

    function hideBubbleImmediate() {
        clearBubbleTimer();
        bubbleCycleToken += 1;
        bubble.classList.remove('open');
        if (bubbleText) bubbleText.classList.remove('fading');
    }

    function scheduleBubbleCycle(delay) {
        clearBubbleTimer();
        bubbleTimer = setTimeout(runBubbleCycle, delay);
    }

    function runBubbleCycle() {
        if (iframe.classList.contains('active') || container.style.display === 'none') {
            scheduleBubbleCycle(1000);
            return;
        }

        const token = ++bubbleCycleToken;
        if (bubbleText) {
            bubbleText.classList.remove('fading');
            bubbleText.textContent = bubbleMessages[bubbleIndex];
        }
        bubble.classList.add('open');

        bubbleTimer = setTimeout(() => {
            if (token !== bubbleCycleToken) return;
            if (bubbleText) bubbleText.classList.add('fading');

            bubbleTimer = setTimeout(() => {
                if (token !== bubbleCycleToken) return;
                bubble.classList.remove('open');
                bubbleIndex = (bubbleIndex + 1) % bubbleMessages.length;
                if (bubbleText) {
                    bubbleText.textContent = bubbleMessages[bubbleIndex];
                    bubbleText.classList.remove('fading');
                }
                scheduleBubbleCycle(BUBBLE_CLOSED_MS);
            }, 260);
        }, BUBBLE_OPEN_MS);
    }

    const openChat = () => {
        hideBubbleImmediate();
        iframe.classList.add('active');
        container.style.display = 'none';
        const notifyTrafficOpen = () => {
            try {
                iframe.contentWindow?.postMessage({ type: 'svsu-log-traffic' }, CHATBOT_ORIGIN);
            } catch (err) {
                // Ignore postMessage timing issues; the chat stays usable.
            }
        };
        notifyTrafficOpen();
        setTimeout(notifyTrafficOpen, 500);
    };
    launcher.onclick = openChat;
    bubble.onclick = openChat;

    scheduleBubbleCycle(700);

    window.addEventListener('message', function(event) {
        const fromChatIframe = event.source === iframe.contentWindow;
        const allowedOrigin = CHATBOT_ORIGIN;

        if (!fromChatIframe && event.origin !== allowedOrigin) return;
        if (event.data === 'chatClosed') {
            iframe.classList.remove('active');
            container.style.display = 'flex';
            scheduleBubbleCycle(500);
        }
    });
})();
