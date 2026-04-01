import { renderAgents } from "./components/agent-table.js" 
import { subscribe, refreshAgents } from "./stores/agent-store.js"
import { loadEventSummary, loadRecentEvents, refreshEvents } from "./components/recent-events.js"
import "./components/agent-map.js"


// load once
loadEventSummary()
loadRecentEvents()
subscribe(renderAgents)
refreshAgents()

// refresh agents every 5 seconds
setInterval(refreshAgents, 5000)
setInterval(refreshEvents, 5000)
