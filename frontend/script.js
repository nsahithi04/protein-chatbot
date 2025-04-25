const socket = io("http://127.0.0.1:5000"); // Backend server URL
socket.on("connect", () => {
  console.log("✅ Socket.IO connected to backend!");
});

function displayMessage(message, sender = "bot") {
  const chatBox = document.getElementById("chat-box");
  const messageDiv = document.createElement("div");
  messageDiv.classList.add("chat-message", sender + "-message");
  messageDiv.innerHTML = `<p>${message}</p>`;
  chatBox.appendChild(messageDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function sendMessage() {
  const userInput = document.getElementById("user-input").value;
  if (!userInput.trim()) return;

  // Display the user's message in the chat
  displayMessage(userInput, "user");

  // Clear input field
  document.getElementById("user-input").value = "";

  // Show typing indicator for bot (this will be removed after the delay)
  const typingIndicator = document.createElement("div");
  typingIndicator.classList.add(
    "chat-message",
    "bot-message",
    "typing-indicator"
  );
  typingIndicator.innerHTML = "<p>typing...</p>";
  document.getElementById("chat-box").appendChild(typingIndicator);

  // Emit user message to backend
  socket.emit("user_message", userInput);

  // Simulate delay before bot responds (typing effect)
  setTimeout(function () {
    // Remove typing indicator after a delay
    typingIndicator.remove();
  }, 1500); // Adjust the typing delay (1.5s for example)
}

socket.on("bot_response", (data) => {
  // Show bot response after receiving it from the backend
  displayMessage(data.message, "bot"); // Only display the actual response from bot
});

// Function to append the 3D viewer button when relevant
function appendProteinViewerButton(uniprotId) {
  const chatBox = document.getElementById("chat-box");
  const msgDiv = document.createElement("div");
  msgDiv.className = "chat-message bot-message";
  msgDiv.innerHTML = `
    <p>🔍 Here's the 3D structure for <b>${uniprotId}</b>:</p>
    <button onclick="viewStructure('${uniprotId}')">🔬 View 3D Structure</button>
  `;
  chatBox.appendChild(msgDiv);
}

// Function to view protein structure (just a placeholder)
function viewStructure(uniprotId) {
  alert(`Viewing 3D structure for: ${uniprotId}`);
}
