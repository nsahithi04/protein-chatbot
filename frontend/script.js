const socket = io('http://127.0.0.1:5000');  // Backend server URL
socket.on('connect', () => {
  console.log('✅ Socket.IO connected to backend!');
});

// Function to display messages in the chat box
function displayMessage(message, sender = 'bot') {
  const chatBox = document.getElementById('chat-box');
  const messageDiv = document.createElement('div');
  messageDiv.classList.add('chat-message', sender + '-message');
  messageDiv.innerHTML = `<p>${message}</p>`;
  chatBox.appendChild(messageDiv);
  chatBox.scrollTop = chatBox.scrollHeight;  // Scroll to the latest message
}

// Function to handle user input
function sendMessage() {
  const userInput = document.getElementById('user-input').value;
  if (!userInput.trim()) return;

  displayMessage(userInput, 'user');  // Display user message

  // Send user input to the backend via SocketIO
  socket.emit('user_message', userInput);

  // Clear the input field
  document.getElementById('user-input').value = '';
}

// Listen for the bot's response from the backend
socket.on('bot_response', (data) => {
  displayMessage(data.message, 'bot');
});
