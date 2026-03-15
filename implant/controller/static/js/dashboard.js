import { renderAgents } from "./components/agent-card.js" 
import { subscribe, refreshAgents } from "./stores/agent-store.js"


// load once
subscribe(renderAgents)
refreshAgents()

// refresh agents every 5 seconds
setInterval(refreshAgents, 5000)
