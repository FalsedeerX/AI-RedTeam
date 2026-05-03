const subscribers = []

let state = {
	agents: [],
	loading: true,
	filters: {
		// support null, "online" and "offline"
		"status": null
	}
}


// subscribe a callback function to store updates
export function subscribe(callback) {
	subscribers.push(callback)
}


// notify and invoke callback of subscribers
function notify() {
	subscribers.forEach(callbackFunc => callbackFunc(state))
}


// set query filters
export function setFilter(key, value) {
	if (!Object.hasOwn(state.filters, key)) {
		throw new Error(`Invalid filter key: ${key}`)
	}

	// set filter and force immediate refresh
	state.filters[key] = value
	refreshAgents()
}


// fetch list of agents from the backend
export async function refreshAgents() {
	try {
		// build the query and fetch backend
		const params = new URLSearchParams()
		for (const [key, value] of Object.entries(state.filters)) {
			if (value != null) {
				params.set(key, value)
			}
		}

		// send request to backend
		const response = await fetch(`/api/dashboard/agents?${params.toString()}`)
		if (!response.ok) throw new Error("Failed to fetch agents")
		state.agents = await response.json()
		state.loading = false

	} catch (err) {
		console.error("Agent fetch error:", err)
		state.loading = true

	} finally {
		// notify subscribers
		notify()
	}
}
