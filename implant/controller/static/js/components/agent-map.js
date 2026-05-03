// initilize the map
var map = L.map('map').setView([0, 0], 2)
L.tileLayer('https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png', {
	minZoom: 0,
	maxZoom: 20
}).addTo(map)
