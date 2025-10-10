document.addEventListener('DOMContentLoaded', () => {
    // DOM elements
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    
    // API endpoint
    const API_URL = 'http://localhost:8000';
    
    // Function to add a message to the chat
    function addMessage(content, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const messageParagraph = document.createElement('p');
        messageParagraph.textContent = content;
        
        messageContent.appendChild(messageParagraph);
        messageDiv.appendChild(messageContent);
        chatMessages.appendChild(messageDiv);
        
        // Scroll to the bottom of the chat
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Function to show typing indicator
    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator bot-message';
        typingDiv.id = 'typing-indicator';
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('span');
            typingDiv.appendChild(dot);
        }
        
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Function to remove typing indicator
    function removeTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    // Function to send a message to the API
    async function sendMessage(message) {
        try {
            showTypingIndicator();
            
            const response = await fetch(`${API_URL}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });
            
            if (!response.ok) {
                throw new Error('Failed to get response from the server');
            }
            
            const data = await response.json();
            removeTypingIndicator();
            addMessage(data.response);
            
        } catch (error) {
            console.error('Error:', error);
            removeTypingIndicator();
            addMessage('Sorry, I encountered an error. Please try again later.');
        }
    }
    
    // Event listener for send button
    sendButton.addEventListener('click', () => {
        const message = userInput.value.trim();
        if (message) {
            addMessage(message, true);
            userInput.value = '';
            sendMessage(message);
        }
    });
    
    // Event listener for Enter key
    userInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            const message = userInput.value.trim();
            if (message) {
                addMessage(message, true);
                userInput.value = '';
                sendMessage(message);
            }
        }
    });
    
    // Load previous conversations on page load
    async function loadPreviousConversations() {
        try {
            const response = await fetch(`${API_URL}/conversations?limit=5`);
            
            if (!response.ok) {
                return; // Silently fail if we can't load previous conversations
            }
            
            const conversations = await response.json();
            
            // Clear the default welcome message
            chatMessages.innerHTML = '';
            
            if (conversations.length === 0) {
                // If no previous conversations, show welcome message
                addMessage('Hello! I\'m your AI assistant. How can I help you today?');
            } else {
                // Add previous conversations to the chat
                conversations.reverse().forEach(conv => {
                    addMessage(conv.user_message, true);
                    addMessage(conv.bot_response);
                });
            }
            
        } catch (error) {
            console.error('Error loading previous conversations:', error);
            // Show default welcome message if we can't load previous conversations
            addMessage('Hello! I\'m your AI assistant. How can I help you today?');
        }
    }
    
    // Load previous conversations when the page loads
    loadPreviousConversations();
});
