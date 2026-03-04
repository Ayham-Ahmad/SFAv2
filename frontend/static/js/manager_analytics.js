async function sendMessage() {
    const inputField = document.getElementById("user-input");
    const chatMessages = document.getElementById("chat-messages");
    const statusIndicator = document.getElementById("status-indicator");
    const message = inputField.value.trim();

    if (!message) return;

    appendMessage("user", message);
    inputField.value = "";

    statusIndicator.style.display = "block";

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: message})
        });

        const data = await response.json();

        if (data.success) {
            appendMessage("bot", data.message);
        } else {
            appendMessage("bot", "Error: " + data.message);
        }
    } catch (error) {
        console.error("Chat Error:", error);
        appendMessage("bot", "Could not connect to the server.");
    } finally {
        statusIndicator.style.display = "none";
    }
}

function appendMessage(sender, text) {
    const chatMessages = document.getElementById("chat-messages");
    const msgDiv = document.createElement("div");
    
    // Add classes based on sender
    msgDiv.className = sender === "user" ? "message user-msg shadow-sm" : "message bot-msg shadow-sm";
    
    // Convert Markdown to HTML (since we included marked.js in the HTML)
    const formattedText = typeof marked !== 'undefined' ? marked.parse(text) : text;
    
    msgDiv.innerHTML = `
        <div class="fw-bold mb-1">
            <i class="fas ${sender === 'user' ? 'fa-user' : 'fa-robot'} me-1"></i>
            ${sender === 'user' ? 'You' : 'SFA'}
        </div>
        <div>${formattedText}</div>
    `;
    
    chatMessages.appendChild(msgDiv);
    
    // Auto-scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Allow pressing "Enter" to send
document.getElementById("user-input").addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
});