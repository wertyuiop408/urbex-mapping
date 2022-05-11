class searchBar {

    constructor(options) {}
    onAdd(map) {
        this._map = map;

        const el = document.createElement('div');
        el.className = 'mapboxgl-ctrl-geocoder mapboxgl-ctrl';

    
        const searchIcon = this.createIcon('search', '<path d="M7.4 2.5c-2.7 0-4.9 2.2-4.9 4.9s2.2 4.9 4.9 4.9c1 0 1.8-.2 2.5-.8l3.7 3.7c.2.2.4.3.8.3.7 0 1.1-.4 1.1-1.1 0-.3-.1-.5-.3-.8L11.4 10c.4-.8.8-1.6.8-2.5.1-2.8-2.1-5-4.8-5zm0 1.6c1.8 0 3.2 1.4 3.2 3.2s-1.4 3.2-3.2 3.2-3.3-1.3-3.3-3.1 1.4-3.3 3.3-3.3z"/>')
        el.appendChild(searchIcon)


        this._inputEl = document.createElement('input');
        this._inputEl.type = 'text';
        this._inputEl.className = 'mapboxgl-ctrl-geocoder--input';
        this._inputEl.placeholder = "Search";
        this._inputEl.setAttribute('aria-label', "Search");
        
        this._onKeyDown = this._onKeyDown.bind(this);
        this._inputEl.addEventListener('keydown', this.debounce(this._onKeyDown, 200));

        this._onChange = this._onChange.bind(this);
        this._inputEl.addEventListener('change', this._onChange);
        el.appendChild(this._inputEl);

        this._typeahead = new Suggestions(this._inputEl, [])
        this._typeahead.render = function(item) {
            return '<div class="mapboxgl-ctrl-geocoder--suggestion"><div class="mapboxgl-ctrl-geocoder--suggestion-title">' + item.properties.name + '</div><div class="mapboxgl-ctrl-geocoder--suggestion-address">' + item.properties.loc + '</div></div>';
        }
        this._typeahead.getItemValue = function(item) {
          return item.properties.name
        }

        const actions = document.createElement('div');
        actions.classList.add('mapboxgl-ctrl-geocoder--pin-right');

        this._clearEl = document.createElement('button');
        this._clearEl.setAttribute('aria-label', 'Clear');
        this._clearEl.addEventListener('click', () => {this._inputEl.value = '';this._clearEl.style.display = 'none'});//does this work?
        this._clearEl.className = 'mapboxgl-ctrl-geocoder--button';

        const buttonIcon = this.createIcon('close', '<path d="M3.8 2.5c-.6 0-1.3.7-1.3 1.3 0 .3.2.7.5.8L7.2 9 3 13.2c-.3.3-.5.7-.5 1 0 .6.7 1.3 1.3 1.3.3 0 .7-.2 1-.5L9 10.8l4.2 4.2c.2.3.7.3 1 .3.6 0 1.3-.7 1.3-1.3 0-.3-.2-.7-.3-1l-4.4-4L15 4.6c.3-.2.5-.5.5-.8 0-.7-.7-1.3-1.3-1.3-.3 0-.7.2-1 .3L9 7.1 4.8 2.8c-.3-.1-.7-.3-1-.3z"/>')
        this._clearEl.appendChild(buttonIcon);
        actions.appendChild(this._clearEl);

        this._loadingEl = this.createIcon('loading', '<path fill="#333" d="M4.4 4.4l.8.8c2.1-2.1 5.5-2.1 7.6 0l.8-.8c-2.5-2.5-6.7-2.5-9.2 0z"/><path opacity=".1" d="M12.8 12.9c-2.1 2.1-5.5 2.1-7.6 0-2.1-2.1-2.1-5.5 0-7.7l-.8-.8c-2.5 2.5-2.5 6.7 0 9.2s6.6 2.5 9.2 0 2.5-6.6 0-9.2l-.8.8c2.2 2.1 2.2 5.6 0 7.7z"/>');
        actions.appendChild(this._loadingEl);
        
        el.appendChild(actions);


        
        this._container = el;
        return this._container;
    }


    onRemove() {

        this._container.parentNode.removeChild(this._container);
        this._map = undefined;
        return this;
    }
    createIcon(name, path) {
        var icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        icon.setAttribute('class', `mapboxgl-ctrl-geocoder--icon mapboxgl-ctrl-geocoder--icon-${name}`);
        icon.setAttribute('viewBox', '0 0 18 18');
        icon.setAttribute('xml:space','preserve');
        icon.setAttribute('width', 18);
        icon.setAttribute('height', 18);
        icon.innerHTML = path;
        return icon;
    }
    _onKeyDown() {

        this._loadingEl.style.display = 'block';
        this._typeahead.clear();
        this._typeahead.selected = true;
        
        if (this._inputEl.value.length < 3) return

        self = this;
        const res = fetch(`http://localhost:5000/search/${this._inputEl.value}`)
        .then(response => response.json())
        .then(data => {
            self._loadingEl.style.display = 'none';
            self._clearEl.style.display = 'block';
            self._typeahead.update(data.features);

        });
        
    }

    _onChange() {
        //fires twice -- https://github.com/tristen/suggestions/issues/13 https://github.com/mapbox/mapbox-gl-geocoder/issues/99
        
        this._map.flyTo({
            center: this._typeahead.selected.geometry.coordinates,
            zoom: 13
        });
        
    }


    debounce(fn, wait = 0, { maxWait = Infinity } = {}) {
        //https://dev.to/miketalbot/14-functions-so-you-can-dump-lodash-and-reduce-your-bundle-size-3gg9
        let timer = 0
        let startTime = 0
        let running = false
        let pendingParams
        let result = function (...params) {
            pendingParams = params
            if (running && Date.now() - startTime > maxWait) {
                execute()
            } else {
                if (!running) {
                    startTime = Date.now()
                }
                running = true
            }

            clearTimeout(timer)
            timer = setTimeout(execute, Math.min(maxWait - startTime, wait))

            function execute() {
                running = false
                fn(...params)
            }
        }
        result.flush = function () {
            if (running) {
                running = false
                clearTimeout(timer)
                fn(...pendingParams)
            }
        }
        result.cancel = function () {
            running = false
            clearTimeout(timer)
        }
        return result
    }

}





function def_vals() {
    //default values
    const params = (new URL(document.location)).searchParams;
    const param = params.get('l');
    const loc = (param)?param.split(','):[]
    const def = {};
    [def.lat=51.740615, def.lng=-2.224585, def.zoom=13] = loc
    return def
}
defaults = def_vals()

//public key
mapboxgl.accessToken = "pk.eyJ1Ijoid2VydHl1aW9wNDA4IiwiYSI6ImNreW1yd2NwcjNpbnAyb3A4dzVoYThlczcifQ.Z7Ysk6cBE7VmZArynxX9Kw";
const map = new mapboxgl.Map({
    container: "map", // container ID
    style: "mapbox://styles/mapbox/streets-v11", // style URL
    center: [defaults.lng, defaults.lat], // starting position [lng, lat]
    zoom: defaults.zoom, // starting zoom
    pitchWithRotate: false
});

const layerList = document.getElementById("menu");
const inputs = layerList.getElementsByTagName("input");
 
for (const input of inputs) {
    input.onclick = (layer) => {
        const layerId = layer.target.id;
        map.setStyle("mapbox://styles/mapbox/" + layerId);
    };
}
map.on("style.load", load_data);


map.on("click", ["places", "cluster", "cluster-count"], (e) => {
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
map.on("mouseenter", ["places", "cluster", "cluster-count"], (e) => {
    map.getCanvas().style.cursor = "pointer";
    if (e.features[0].layer.id != "places") return

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
map.on("mouseleave", ["places", "cluster", "cluster-count"], () => {
    map.getCanvas().style.cursor = "";
    popup.remove();
});

map.on("load", () => {
    map.addControl(new searchBar());//searchbar

    // Add zoom and rotation controls to the map.
    map.addControl(new mapboxgl.NavigationControl());
    load_data()
});
if (window.location.host != "wertyuiop408.github.io") {
    map.on("moveend", load_data)
}

function load_data() {
    document.querySelector(".mapboxgl-canvas").focus();

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
        "data": data_url,
        "buffer": 0,
        "cluster": true,
        "clusterMaxZoom": 14,
        "clusterRadius": 50
    });

    //general marker
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
        "filter": ["!", ["has", "point_count"]]
    });

    //clustered group
    map.addLayer({
        "id": "cluster",
        "type": "circle",
        "source": "places",
        "paint": {
            "circle-color": "#fc4e2a",
            "circle-radius": 20
        },
        "filter": ["has", "point_count"]
    });

    //clustered group count
    map.addLayer({
        "id": "cluster-count",
        "type": "symbol",
        "source": "places",
        "layout": {
            "text-field": "{point_count_abbreviated}",
            "text-font": ["DIN Offc Pro Medium", "Arial Unicode MS Bold"],
            "text-size": 12
        },
        "filter": ["has", "point_count"]
    });
}