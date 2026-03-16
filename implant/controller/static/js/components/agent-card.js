export function renderAgents(state) {
	// backend unreachable or not ready
	if (state.loading) {
		renderAgentsSkeleton()
		return
	}
	
	// clear content of <tbody> tag in table "agents" before render
	const tbody = document.querySelector("#agents tbody")
	tbody.innerHTML = ""

	// update the DOM inplace
	state.agents.forEach(agent => {
		const row = tbody.insertRow()
		row.insertCell().innerText = agent.agent_id
		row.insertCell().innerText = agent.ip_address
		row.insertCell().innerText = agent.created_at
		row.insertCell().innerText = agent.last_seen
	
		// add control button
		const cell = row.insertCell()
		const manage = document.createElement("a")
		manage.href = `/manage/${agent.agent_id}`
		manage.className = "btn btn-primary btn-sm me-2"
		manage.innerText = "Manage"
		cell.appendChild(manage)

		// add delete button
		const del = document.createElement("button")
		del.className = "btn btn-danger btn-sm"
		del.innerText = "Delete"
		del.addEventListener("click", async () => {
			if (!confirm(`Delete agent ${agent.agent_id} ?`)) return
			
			await fetch(`/api/dashboard/agents/${agent.agent_id}`, {
				method: "DELETE"
			})
			row.remove()
		})
		cell.appendChild(del)
	})
}


function renderAgentsSkeleton(rowCount = 5) {
	// clear content of <tbody> tag in table "agents" before render
	const tbody = document.querySelector("#agents tbody")
	tbody.innerHTML = ""

	// update the DOM inplace
	for (let i = 0; i < rowCount; i++) {
		const row = tbody.insertRow()
		
		// add placeholder for agent info display
		for (let j = 0; j < 4; j++) {
			const cell = row.insertCell()
			cell.innerHTML = `
			<span class="placeholder-glow">
				<span class="placeholder col-10"></span>
			</span>
			`
		}

		// add placeholder for control button
		const cell = row.insertCell()
		cell.innerHTML = `
		<span class="placeholder-glow">
			<span class="placeholder col-8"></span>
		</span>
		`
	}
}
