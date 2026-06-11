async function sendMessage() {
    const inputField = document.getElementById("user-input");
    const statusIndicator = document.getElementById("status-indicator");
    const message = inputField.value.trim();

    const sendBtn = document.getElementById("send-btn");
    const stopBtn = document.getElementById("stop-btn");

    if (!message) return;

    appendMessage("user", message);
    inputField.value = "";
    statusIndicator.style.display = "block";
    sendBtn.style.display = "none";
    stopBtn.style.display = "block";
    stopBtn.disabled = false;

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: message }),
        });
        const data = await response.json();
        
        if (data.message) {
            appendMessage("bot", data.message);
        }
        
        if (data.success && data.data && data.data.graphs) {
            renderGraphs(data.data.graphs);
        }
    } catch (error) {
        console.error("Chat Error:", error);
        appendMessage("bot", "Could not connect to the server.");
    } finally {
        statusIndicator.style.display = "none";
        sendBtn.style.display = "block";
        stopBtn.style.display = "none";
        inputField.focus();
    }
}

function appendMessage(sender, text) {
    const chatMessages = document.getElementById("chat-messages");
    const msgDiv = document.createElement("div");
    msgDiv.className = sender === "user" ? "message user-msg shadow-sm" : "message bot-msg shadow-sm";

    const formattedText = typeof marked !== "undefined" ? marked.parse(text) : text;

    msgDiv.innerHTML = `
        <div class="fw-bold mb-1">
            <i class="fas ${sender === "user" ? "fa-user" : "fa-robot"} me-1"></i>
            ${sender === "user" ? "You" : "SFA"}
        </div>
        <div>${formattedText}</div>`;

    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function stopQuery() {
    const stopBtn = document.getElementById("stop-btn");
    if (stopBtn) stopBtn.disabled = true;

    try {
        await fetch("/api/chat/stop", {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });
    } catch (error) {
        console.error("Failed to send stop signal:", error);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const userInput = document.getElementById("user-input");
    
    if (userInput) {
        userInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                e.preventDefault(); 
                sendMessage();
            }
        });
    }
});

function renderGraphs(graphs) {
    const graphsTrack = document.getElementById("graphs-track");
    if (!graphsTrack) return;

    graphs.forEach(config => {
        const graphId = `graph-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
        const colDiv = document.createElement("div");
        colDiv.className = "graph-card-container mb-4";
        colDiv.innerHTML = `
            <div class="card shadow-sm border-0 h-100">
                <div class="card-header bg-white border-0 py-3 d-flex justify-content-between align-items-center">
                    <h5 class="card-title mb-0 fw-bold text-dark">${config.title || "Financial Graph"}</h5>
                    <div class="graph-actions">
                        <button class="btn btn-sm btn-link text-danger p-0" onclick="this.closest('.graph-card-container').remove()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
                <div class="card-body p-2">
                    <div id="${graphId}" style="width:100%; height:350px;"></div>
                </div>
            </div>
        `;
        
        graphsTrack.prepend(colDiv);

        let plotData = [];
        
        if (config.series && Array.isArray(config.series)) {
            // Support for combo charts and multiple series
            config.series.forEach(s => {
                const yColName = s.column || config.y_column;
                const axisType = s.y_axis === 'y2' ? 'y2' : 'y1';
                
                plotData.push({
                    x: config.data.map(d => d[config.x_column]),
                    y: config.data.map(d => d[yColName]),
                    type: s.type === 'bar' ? 'bar' : 'scatter',
                    mode: s.type === 'line' ? 'lines+markers' : undefined,
                    name: yColName,
                    yaxis: axisType,
                    line: s.type === 'line' ? { shape: 'spline', width: 3 } : undefined
                });
            });
        } else {
            // Standard single-series chart
            plotData.push({
                x: config.data.map(d => d[config.x_column]),
                y: config.data.map(d => d[config.y_column]),
                type: config.graph_type === 'bar' ? 'bar' : 'scatter',
                mode: config.graph_type === 'line' ? 'lines+markers' : undefined,
                marker: { color: '#0ea5e9' },
                line: { shape: 'spline', color: '#0ea5e9', width: 3 },
                name: config.y_column
            });
        }

        const layout = {
            margin: { t: 10, r: 20, l: 50, b: 50 },
            xaxis: { title: config.x_column, gridcolor: '#f1f5f9' },
            yaxis: { title: config.y_column || "Value", gridcolor: '#f1f5f9' },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { family: 'Inter, sans-serif' },
            showlegend: (config.series && config.series.length > 1) ? true : false
        };

        if (config.series && config.series.some(s => s.y_axis === 'y2')) {
            const y2Title = (config.axis_titles && config.axis_titles.y2) ? config.axis_titles.y2.title : 'Secondary Axis';
            layout.yaxis2 = {
                title: y2Title,
                overlaying: 'y',
                side: 'right',
                gridcolor: '#f1f5f9'
            };
        }

        const plotConfig = { responsive: true, displayModeBar: false };

        Plotly.newPlot(graphId, plotData, layout, plotConfig);
    });
}