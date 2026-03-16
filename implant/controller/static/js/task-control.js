// client's ID will be injected to var: agentId
let trackingList = []
let currentSchema = null
const taskForm = document.getElementById("task-form") 
const taskSelect = document.getElementById("task-select")
const inputContainer = document.getElementById("task-inputs")
document.addEventListener("DOMContentLoaded", init)


async function init() {
	await loadSupportedTasks()

	// add callback func upon user change task selection 
	taskSelect.addEventListener("change", onTaskChange)

	// add callback func upon user hit submit
	taskForm.addEventListener("submit", onSubmit)

	// trigger form render on the default task selection
	if (taskSelect.value) {
		await onTaskChange()
	}

	// auto poll result every 2 seconds
	setInterval(pollTaskResult, 2000)
}


async function onTaskChange() {
	const taskName = taskSelect.value
	const schema = await loadTaskSchema(taskName)
	currentSchema = schema

	// render the dynamic DOM
	renderTaskMetadata(schema)
	renderForm(schema)
}


async function loadSupportedTasks() {
	const response = await fetch("/api/dashboard/capabilities/tasks")
	const taskSummaries = await response.json()

	// populate our drop-down list
	taskSummaries.forEach(task => {
		const option = document.createElement("option")
		option.value = task.name
		option.textContent = task.name
		taskSelect.appendChild(option)
	})
}


async function loadTaskSchema(taskName) {
	const response = await fetch(`/api/dashboard/capabilities/tasks/${taskName}`)
	const schema = response.json()
	return schema
}


function renderTaskMetadata(schema) {
	const metadata = document.getElementById("task-metadata")
	metadata.innerHTML = `Version: ${schema.version}<br>${schema.description}`
}


function renderForm(schema) {
	// reset previous content before rendering
	inputContainer.innerHTML = ""
	schema.params.forEach(param => {
		// create placeholder label
		const label = document.createElement("label")
		label.textContent = param.label

		// create input field
		const input = document.createElement("input")
		input.name = param.field
		input.type = "text"

		// wrap the label and input box in <div>
		row = document.createElement("div")
		row.appendChild(label)
		row.appendChild(input)
		inputContainer.appendChild(row)
	})
}


async function onSubmit(event) {
	// block default submit event
	event.preventDefault()

	// auto harvest form input in key:value pair
	const formData = new FormData(taskForm)
	const params = Object.fromEntries(formData.entries())
	const payload = {
		agent_id: agentId,
		task_name: currentSchema.name,
		params: params
	}

	// scheudle task and add tracking on task id
	const response = await fetch("/api/dashboard/tasks", {
		method: "POST",
		headers: {"Content-Type": "application/json"},
		body: JSON.stringify(payload)
	})
	
	// ensure endpont respond with 201 created
	if (response.status != 201) {
		alert(`Task scheduling failed (status ${response.status})`)
		return
	}

	// if succeed, add task id to tracking list
	const data = await response.json()
	const taskId = data.task_id
	trackingList.push(taskId)

	// notify user and clear input
	alert(`Task #${taskId.slice(0, 8)} scheduled`)
	taskForm.reset()
}


function renderOutput(taskId, data) {
	const output = document.getElementById("output")
	const message = 
`=======================================================
Task ID: ${taskId}
-------------------------------------------------------
${data}

`
	// append data, auto scroll to bottom
	output.textContent += message
	output.scrollTop = output.scrollHeight
}


function untrackTask(taskId) {
	// locate item position in list and remove it
	const index = trackingList.indexOf(taskId)
	if (index != -1) {
		trackingList.splice(index, 1)
	}
}


async function pollTaskResult() {
	// iterate trackingList to check for complete
	if (trackingList.length == 0) return
	for (const taskId of trackingList) {
		const response = await fetch(`/api/dashboard/tasks/${taskId}`)
		const data = await response.json()

		// if completed, remove tracking and render on screen
		if (data.completed) {
			renderOutput(taskId, data.output)
			untrackTask(taskId)	
		}
	}
}



