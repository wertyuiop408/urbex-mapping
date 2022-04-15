//public key
mapboxgl.accessToken = "pk.eyJ1Ijoid2VydHl1aW9wNDA4IiwiYSI6ImNreW1yd2NwcjNpbnAyb3A4dzVoYThlczcifQ.Z7Ysk6cBE7VmZArynxX9Kw";
const map = new mapboxgl.Map({
    container: "map", // container ID
    style: "mapbox://styles/mapbox/streets-v11", // style URL
    center: [-2.224585, 51.740615], // starting position [lng, lat]
    zoom: 13, // starting zoom
    pitchWithRotate: false
});

// Add zoom and rotation controls to the map.
map.addControl(new mapboxgl.NavigationControl());
const layerList = document.getElementById("menu");
const inputs = layerList.getElementsByTagName("input");
 
for (const input of inputs) {
    input.onclick = (layer) => {
        const layerId = layer.target.id;
        map.setStyle("mapbox://styles/mapbox/" + layerId);
    };
}
map.on("style.load", load_data);


map.on("click", "places", (e) => {
    map.flyTo({
        center: e.features[0].geometry.coordinates
    });
});


// Create a popup, but don"t add it to the map yet.
const popup = new mapboxgl.Popup({
    closeButton: false,
    closeOnClick: false
});

// Change the cursor to a pointer when the it enters a feature in the "circle" layer.
map.on("mouseenter", "places", (e) => {
    map.getCanvas().style.cursor = "pointer";

    // Copy coordinates array.
    const coordinates = e.features[0].geometry.coordinates.slice();
    const description = `${e.features[0].properties.name}<br/>
        ${coordinates[1].toFixed(5)}, ${coordinates[0].toFixed(5)}
    `;
    

     
    // Ensure that if the map is zoomed out such that multiple
    // copies of the feature are visible, the popup appears
    // over the copy being pointed to.
    while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
        coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
    }
     
    // Populate the popup and set its coordinates
    // based on the feature found.
    popup.setLngLat(coordinates).setHTML(description).addTo(map);

});

// Change it back to a pointer when it leaves.
map.on("mouseleave", "places", () => {
    map.getCanvas().style.cursor = "";
    popup.remove();
});

map.on("load", load_data);
if (window.location.host != "wertyuiop408.github.io") {
    map.on("moveend", load_data)
}

function load_data() {
    const source = map.getSource("places")
    const bounds = map.getBounds()
    let data_url = `http://localhost:5000/bounds/${bounds._ne.lat}/${bounds._ne.lng}/${bounds._sw.lat}/${bounds._sw.lng}`
    if (window.location.host == "wertyuiop408.github.io") {
        data_url = "./data.json"
    }
    if (source) {
        source.setData(data_url)
        return
    }

    map.addSource("places", {
        "type": "geojson",
        "data": data_url
    });

    map.addLayer({
        "id": "places",
        "type": "circle",
        "source": "places",
        "paint": {
            "circle-color": "#4264fb",
            "circle-radius": 8,
            "circle-stroke-width": 2,
            "circle-stroke-color": "#ffffff"
        },
        "filter": ["==", "$type", "Point"]
    });
}