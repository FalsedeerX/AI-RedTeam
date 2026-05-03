export async function loadRegisteredTasks() {
	const response = await fetch("/api/dashboard/capabilities/tasks")
	const taskSummaries = await response.json()
	renderRegisteredTasks(taskSummaries)
}


function renderRegisteredTasks(taskSummaries) {
	// clear content of <tbody> tag in table "registered-tasks" before render
	const tbody = document.querySelector("#registered-tasks tbody")
	tbody.innerHTML = ""

	// update the DOM inplace
	taskSummaries.forEach(summary => {
		const row = tbody.insertRow()
		row.insertCell().innerText = summary.name
		row.insertCell().innerText = summary.version
		row.insertCell().innerText = summary.description
		row.insertCell().innerText = summary.parameter_count
	})
}

