let eventCursor = null
const maxEvents = 100
const eventStyle = {
	debug: {
		icon: "bi bi-bug-fill",
		color: "text-secondary"
	},
	info: {
		icon: "bi bi-info-circle-fill",
		color: "text-primary"
	},
	warning: {
		icon: "bi bi-cone-striped",
		color: "text-info"
	},
	error: {
		icon: "bi bi-exclamation-triangle-fill",
		color: "text-warning"
	},
	critical: {
		icon: "bi bi-x-octagon-fill",
		color: "text-danger"
	}
}


export async function loadEventSummary() {
	const response = await fetch("/api/dashboard/events/summary")
	const eventSummary = await response.json()
	renderEventSummary(eventSummary)
}


export async function loadRecentEvents() {
	let url = `/api/dashboard/events?limit=${maxEvents}`
	if (eventCursor != null) {
		url += `&cursor=${eventCursor}`
	}

	const response = await fetch(url)
	const payload = await response.json()
	eventCursor = payload.cursor
	renderEvents(payload.events)
}


export function refreshEvents() {
	loadEventSummary()
	loadRecentEvents()
}


function renderEventSummary(eventSummary) {
	const warning_count = document.getElementById("event-warning-count")
	const error_count = document.getElementById("event-error-count")
	const critical_count = document.getElementById("event-critical-count")

	// set value
	warning_count.textContent = eventSummary.warning
	error_count.textContent = eventSummary.error
	critical_count.textContent = eventSummary.critical
}


function renderEvents(events) {
	const eventList = document.getElementById("recent-events")

	events.forEach(event => {
		const style	= eventStyle[event.level]
		const li = document.createElement("li")
		const time = new Date(event.created_at)
		const timeStr = time.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})
		li.className = "list-group-item"

		// add icon, text color and timestamp
		li.innerHTML = `
		<div class="d-flex flex-column overflow-hidden">
    		<div class="d-flex align-items-center overflow-hidden mb-1">
        		<i class="${style.icon} ${style.color} me-2 flex-shrink-0"></i>
        		<div class="overflow-hidden" style="flex: 1 1 0; width: 0;">
            		<span class="text-truncate d-block"
                  		data-bs-toggle="tooltip"
                  		data-bs-placement="top"
                  		title="${event.message}">
                		${event.message}
            		</span>
        		</div>
    		</div>
    		<div class="d-flex justify-content-end">
        		<small class="text-muted">
            		${timeStr}
        		</small>
    		</div>
		</div>
		`

// initialize the tooltip on the new element
const tooltipEl = li.querySelector('[data-bs-toggle="tooltip"]')
new bootstrap.Tooltip(tooltipEl)

		// append entry & purge oldest if overflow
		eventList.appendChild(li)
		eventList.parentElement.scrollTop = eventList.parentElement.scrollHeight
		if (eventList.children.length > maxEvents) {
			const old = eventList.firstChild
			const tip = bootstrap.Tooltip.getInstance(old.querySelector('[data-bs-toggle="tooltip"]'))
			if (tip) tip.dispose()
			eventList.removeChild(old)
		}
	})
}
