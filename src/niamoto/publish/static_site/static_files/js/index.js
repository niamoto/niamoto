function loadCharts(item, mapping) {
    var frequencies = item.frequencies;

    Object.entries(mapping.fields).forEach(function ([field_key, field]) {
        if (field.field_type !== 'GEOGRAPHY') {
            // Chart for bins
            if (field.bins && field.bins.values && field.bins.values.length > 0 && frequencies && frequencies[field.source_field]) {
                var binData = {
                    labels: Object.keys(frequencies[field_key]),
                    datasets: [{
                        label: field.label,
                        data: Object.values(frequencies[field_key]),
                        backgroundColor: field.bins.chart_options.color
                    }]
                };

                var binConfig = {
                    type: field.bins.chart_type,
                    data: binData,
                    options: field.bins.chart_options
                };

                var binCtx = document.getElementById(field_key + 'BinChart').getContext('2d');
                new Chart(binCtx, binConfig);
            }

            // Charts for transformations
            field.transformations.forEach(function (transformation) {
                if (transformation.chart_type === 'text') {
                    var textElement = document.getElementById(field_key + 'Text');
                    if (textElement) {
                        textElement.textContent = item[field_key];
                    }
                } else if (transformation.chart_type === 'pie') {
                    var pieData = {
                        labels: ['True', 'False'],
                        datasets: [{
                            data: [
                                item[field_key + '_true'] || 0,
                                item[field_key + '_false'] || 0
                            ],
                            backgroundColor: ['#FF6384', '#36A2EB']
                        }]
                    };

                    var pieConfig = {
                        type: 'pie',
                        data: pieData,
                        options: {
                            title: {
                                display: true,
                                text: transformation.chart_options.title
                            }
                        }
                    };

                    var pieCtx = document.getElementById(field_key + 'PieChart').getContext('2d');
                    new Chart(pieCtx, pieConfig);
                } else if (transformation.chart_type === 'gauge') {
                    var gaugeOptions = {
                        id: field.source_field + transformation.name + 'Gauge',
                        value: item[field.source_field + '_' + transformation.name],
                        min: 0,
                        max: transformation.chart_options.max,
                        title: transformation.chart_options.title,
                        label: transformation.chart_options.label
                    };

                    createGauge(gaugeOptions);
                } else if (transformation.chart_type == 'bar') {
                        var barData = {
                            labels: Object.keys(item[field_key] || {}),
                            datasets: [{
                                label: field.label,
                                data: Object.values(item[field_key] || {}),
                                backgroundColor: getColor(0).background,
                                borderColor: getColor(0).border,
                                borderWidth: 1
                            }]
                        };

                        var barConfig = {
                            type: 'bar',
                            data: barData,
                            options: transformation.chart_options
                        };

                        var barCtx = document.getElementById(field_key + 'BarChart');
                        if (barCtx) {
                            barCtx = barCtx.getContext('2d');
                            new Chart(barCtx, barConfig);
                        }
                    }
            });
        }
    });
}

function createGauge(options) {
    new JustGage({
        id: options.id,
        value: options.value,
        min: options.min || 0,
        max: options.max,
        title: options.title,
        label: options.label,
        pointer: true,
        pointerOptions: {
            toplength: 10,
            bottomlength: 10,
            bottomwidth: 2,
            color: '#8e8e93',
            stroke: '#ffffff',
            stroke_width: 3,
            stroke_linecap: 'round'
        },
        gaugeWidthScale: 0.6,
        counter: true,
        donut: true,
        relativeGaugeSize: true,
        donutStartAngle: 270,
        hideInnerShadow: true,
        customSectors: [{
            color: "#ff0000",
            lo: 0,
            hi: options.max * 0.33
        }, {
            color: "#ffff00",
            lo: options.max * 0.33,
            hi: options.max * 0.66
        }, {
            color: "#00ff00",
            lo: options.max * 0.66,
            hi: options.max
        }],
        humanFriendly: true,
        formatNumber: true,
    });
}

function createTree(container, taxonomyData) {
    function getBaseUrl() {
        const pathArray = window.location.pathname.split('/');
        pathArray.pop();
        return pathArray.join('/') + '/';
    }

    const baseUrl = getBaseUrl();

    function createList(data) {
        const $ul = $('<ul></ul>');
        $.each(data, function (i, item) {
            const $li = $('<li></li>');
            const $a = $('<a></a>', {
                'href': `${baseUrl}${item.id}.html`,
                'text': item.name,
                'data-id': item.id
            });

            // Appliquez un style spécial au taxon actuel
            if (item.id == taxonId) {
                $a.css({
                    'font-weight': 'bold',
                });
            }

            if (item.children && item.children.length > 0) {
                const $span = $('<span>▸</span>').css({
                    'cursor': 'pointer',
                    'margin-right': '5px'
                });

                const $childUl = createList(item.children).hide();
                $span.click(function (event) {
                    event.stopPropagation();
                    $childUl.toggle();
                    $(this).text($childUl.is(":visible") ? '▾' : '▸');
                });

                $li.append($span).append($a).append($childUl);
            } else {
                $li.append($a);
            }
            $ul.append($li);
        });
        return $ul;
    }


    function openCurrentNode($ul, currentId) {
        const $currentLink = $ul.find(`a[data-id='${currentId}']`);
        if ($currentLink.length > 0) {
            $currentLink.parents('ul').each(function () {
                $(this).show();
                $(this).siblings('span').text('▾');
            });
        }
    }

    const $tree = createList(taxonomyData);
    $(container).append($tree);
    openCurrentNode($tree, taxonId); // Ouvrez le noeud correspondant
}


function initMap() {

    var coordinatesField = null;
    for (var fieldName in mapping.fields) {
        if (mapping.fields[fieldName].field_type === "GEOGRAPHY") {
            coordinatesField = mapping.fields[fieldName].transformations[0].chart_options.coordinates_field;
            break;
        }
    }
    if (coordinatesField) {
        var geoPoints = taxon[coordinatesField];

        const satellite = L.tileLayer.wms("https://carto10.gouv.nc/arcgis/services/fond_imagerie/MapServer/WMSServer", {
            layers: '0',
            format: 'image/png',
            transparent: true,
            attribution: "<a href='http://www.geoportal.gouv.nc/'>Géorep</a> <i> - Gouvernement de la Nouvelle-Calédonie</i>"
        });
        const carte = L.tileLayer.wms('https://carto.gouv.nc/arcgis/services/fond_cartographie/MapServer/WMSServer', {
            layers: '0',
            format: 'image/png',
            transparent: true,
            attribution: "<a href='http://www.geoportal.gouv.nc/'>Géorep</a> <i> - Gouvernement de la Nouvelle-Calédonie</i>"
        });
        const map = L.map('taxonMap', {
            center: [-21.291237, 165.516418],
            minZoom: 6,
            maxZoom: 18,
            layers: [carte, satellite],
            scrollWheelZoom: false
        });
        map.attributionControl.setPrefix(false); // Pour supprimer complètement le préfixe "Powered by Leaflet"
        map.attributionControl.addAttribution("<a href='http://www.geoportal.gouv.nc/'>Géorep</a> <i> - Gouvernement de la Nouvelle-Calédonie</i>");

        const baseMaps = {
            "Carte": carte,
            "Satellite": satellite,
        };

        L.control.layers(baseMaps).addTo(map);

        map.on('load', function () {
            document.getElementById('mapLoader').style.display = 'none';
        });

        if (typeof geoPoints === "string") {
            geoPoints = JSON.parse(geoPoints);
        }

        if (geoPoints && geoPoints.coordinates) {
            geoPoints.coordinates.forEach(function (point) {
                var coord = point.coordinates;
                var count = point.count;

                L.circle([coord[1], coord[0]], {
                    color: '#1fb99d',
                    fillColor: '#00716b',
                    fillOpacity: 0.5,
                    radius: 2000,
                    weight: 1
                }).bindPopup('Occurrences: ' + count).addTo(map);
            });

            if (geoPoints.coordinates.length > 0) {
                var bounds = L.latLngBounds(geoPoints.coordinates.map(point => [point.coordinates[1], point.coordinates[0]]));
                map.fitBounds(bounds);
            }
        } else {
            console.warn("No geographic coordinates found.");
        }
    }
}

// Function to get a color based on the index
function getColor(index) {
    var colors = [
        {background: 'rgba(54, 162, 235, 0.6)', border: 'rgba(54, 162, 235, 1)'},
        {background: 'rgba(75, 192, 192, 0.6)', border: 'rgba(75, 192, 192, 1)'},
        {background: 'rgba(255, 99, 132, 0.6)', border: 'rgba(255, 99, 132, 1)'}
        // Add more colors if necessary
    ];
    return colors[index % colors.length]; // Repeat colors if more keys than defined colors
}

window.createTree = createTree;
window.loadCharts = loadCharts;
window.initMap = initMap;