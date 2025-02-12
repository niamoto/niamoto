function loadCharts(item, mapping) {
    var frequencies = item.frequencies;

    function generateColors(count, defaultColor) {
            if (defaultColor) {
                return Array(count).fill(defaultColor);
            }

            // Function to convert HSL to RGB
            function hslToRgb(h, s, l) {
                let r, g, b;

                if (s === 0) {
                    r = g = b = l; // achromatic
                } else {
                    const hue2rgb = (p, q, t) => {
                        if (t < 0) t += 1;
                        if (t > 1) t -= 1;
                        if (t < 1/6) return p + (q - p) * 6 * t;
                        if (t < 1/2) return q;
                        if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
                        return p;
                    };

                    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
                    const p = 2 * l - q;
                    r = hue2rgb(p, q, h + 1/3);
                    g = hue2rgb(p, q, h);
                    b = hue2rgb(p, q, h - 1/3);
                }

                return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
            }

            // Function to convert RGB to Hex
            function rgbToHex(r, g, b) {
                return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
            }

            // Generate harmonious colors
            return Array.from({ length: count }, (_, i) => {
                // Use golden ratio to spread hues evenly
                const hue = (i * 0.618033988749895) % 1;

                // Vary saturation slightly
                const saturation = 0.5 + (i % 3) * 0.1;

                // Vary lightness to create contrast
                const lightness = 0.4 + (i % 2) * 0.2;

                const [r, g, b] = hslToRgb(hue, saturation, lightness);
                return rgbToHex(r, g, b);
            });
        }

    Object.entries(mapping.fields).forEach(function ([field_key, field]) {
        if (field.field_type !== 'GEOGRAPHY') {
            if (field.label === "DBH") {
                console.log(field)
            }

            // Chart for bins
            if (field.bins && field.bins.values && field.bins.values.length > 0) {
                // Vérification des données de fréquence pour les bins
                if (!frequencies || !frequencies[field.source_field] || Object.keys(frequencies[field.source_field]).length === 0) {
                    var binContainer = document.getElementById(field_key + 'BinChart');
                    if (binContainer) {
                        var container = document.createElement('div');
                        container.className = 'flex items-center justify-center h-64';
                        container.innerHTML = '<p class="text-gray-500 italic">Pas de données disponibles</p>';
                        binContainer.parentNode.replaceChild(container, binContainer);
                    }
                } else {
                    // Création du graphique en barres si données présentes
                    var labels, values;
                    if (field.bins.labels && field.bins.values) {
                        labels = field.bins.labels;
                        values = field.bins.values.map(value => frequencies[field.source_field][value] || 0);
                    } else {
                        var dataArray = Object.entries(frequencies[field.source_field])
                            .map(([label, value]) => ({label, value}))
                            .sort((a, b) => parseFloat(a.label) - parseFloat(b.label));

                        labels = dataArray.map(item => item.label);
                        values = dataArray.map(item => item.value);
                    }

                    if (field.bins.chart_options.indexAxis === 'y') {
                        labels.reverse();
                        values.reverse();
                    }

                    var binData = {
                        labels: labels,
                        datasets: [{
                            label: field.label,
                            data: values,
                            backgroundColor: field.bins.chart_options.color
                        }]
                    };

                    var binConfig = {
                        type: field.bins.chart_type,
                        data: binData,
                        options: Object.assign({}, field.bins.chart_options, {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                x: {
                                    stacked: field.bins.chart_options.stacked || false
                                },
                                y: {
                                    stacked: field.bins.chart_options.stacked || false
                                }
                            },
                            plugins: {
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            return `${context.raw}%`;
                                        }
                                    }
                                },
                                datalabels: {
                                    display: true,
                                    align: 'center',
                                    color: 'black',
                                    formatter: function(value) {
                                        return value + '%';
                                    }
                                }
                            }
                        })
                    };

                    var binCtx = document.getElementById(field_key + 'BinChart');
                    if (binCtx) {
                        new Chart(binCtx.getContext('2d'), binConfig);
                    }
                }
            }

            if (field.transformations) {
                // Charts for transformations
            field.transformations.forEach(function (transformation) {
                if (transformation.chart_type === 'text') {
                    var textElement = document.getElementById(field_key + 'Text');
                    if (textElement) {
                        textElement.textContent = item[field_key + "_" + transformation.name];
                    }
                } else if (transformation.chart_type === 'pie') {
                    var trueLabel = transformation.chart_options.labels?.true || 'True';
                    var falseLabel = transformation.chart_options.labels?.false || 'False';
                    var trueColor = transformation.chart_options.colors?.true || '#FF6384';
                    var falseColor = transformation.chart_options.colors?.false || '#36A2EB';

                    var pieData = {
                        labels: [trueLabel, falseLabel],
                        datasets: [{
                            data: [
                                item[field_key + '_true'] || 0,
                                item[field_key + '_false'] || 0
                            ],
                            backgroundColor: [trueColor, falseColor]
                        }]
                    };

                    var pieConfig = {
                        type: 'pie',
                        data: pieData,
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            layout: {
                                padding: {
                                    top: 5,
                                    bottom: 20,
                                    left: 20,
                                    right: 20
                                }
                            },
                            title: {
                                display: true,
                                text: transformation.chart_options.title
                            },
                            legend: {
                                position: 'bottom',
                                labels: {
                                    boxWidth: 12,
                                    padding: 20
                                }
                            },
                            tooltips: {
                                callbacks: {
                                    label: function(tooltipItem, data) {
                                        var dataset = data.datasets[tooltipItem.datasetIndex];
                                        var total = dataset.data.reduce(function(previousValue, currentValue) {
                                            return previousValue + currentValue;
                                        });
                                        var currentValue = dataset.data[tooltipItem.index];
                                        var percentage = Math.round((currentValue/total) * 100);
                                        return data.labels[tooltipItem.index] + ': ' + percentage + '%';
                                    }
                                }
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
                        label: transformation.chart_options.label,
                    };

                    createGauge(gaugeOptions);
                }

                else if (transformation.name === 'temporal_phenology') {
                    var phenologyData = item[field_key + '_temporal_phenology'];
                    if (phenologyData && phenologyData.data && phenologyData.labels) {

                        var datasets = Object.entries(phenologyData.data).map(([key, values], dataIndex) => {
                        // Utiliser la couleur de la configuration si elle existe, sinon utiliser getColor
                        var color = (transformation.chart_options.colors && transformation.chart_options.colors[key])
                            ? transformation.chart_options.colors[key]
                            : getColor(dataIndex);

                        return {
                            label: key.charAt(0).toUpperCase() + key.slice(1),
                            data: values,
                            backgroundColor: color,
                            borderColor: color,
                            borderWidth: 1
                        };
                    });

                        var chartData = {
                            labels: phenologyData.labels,
                            datasets: datasets
                        };

                        var chartConfig = {
                        type: 'bar',
                        data: chartData,
                        options: {
                            responsive: false,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'bottom',
                                }
                            },
                            scales: {
                                x: {
                                    grid: {
                                        display: false
                                    }
                                },
                                y: {
                                    beginAtZero: true,
                                    title: {
                                        display: true,
                                        text: 'Frequency (%)'
                                    },
                                    grid: {
                                        color: 'rgba(0, 0, 0, 0.1)'
                                    },
                                    ticks: {
                                        stepSize: 5
                                    }
                                }
                            },
                            barPercentage: 0.8,
                            categoryPercentage: 0.9
                        }
                    };

                        var chartCanvas = document.getElementById(field_key + 'TemporalPhenologyChart');
                        if (chartCanvas) {
                            new Chart(chartCanvas.getContext('2d'), chartConfig);
                        }
                    }
                }


                else if (transformation.name !== 'temporal_phenology' && transformation.chart_type === 'bar') {
                    var sortedData = Object.entries(item[field_key+'_'+ transformation.name] || {})
                        .sort((a, b) => b[1] - a[1])
                        .slice(0, transformation.count || 10);

                    var defaultColor = transformation.chart_options.color;
                    var colors = generateColors(sortedData.length, defaultColor);

                    var barData = {
                        labels: sortedData.map(item => item[0]),
                        datasets: [{
                            label: field.label,
                            data: sortedData.map(item => item[1]),
                            backgroundColor: colors,
                            borderColor: colors,
                            borderWidth: 1
                        }]
                    };

                    var barConfig = {
                        type: 'bar',
                        data: barData,
                        options: {
                            indexAxis: 'y',
                            responsive: false,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    display: false
                                },
                            },
                            scales: {
                                x: {
                                    title: {
                                        display: true,
                                        font: {
                                            weight: 'bold'
                                        }
                                    },
                                    ticks: {
                                        font: {
                                            weight: 'bold'
                                        }
                                    }
                                },
                                y: {
                                    ticks: {
                                        font: {
                                            weight: 'bold'
                                        }
                                    }
                                }
                            }
                        }
                    };

                    var fieldKey = field_key + transformation.name;
                    var barCtxElement = document.getElementById(fieldKey + 'BarChart');
                    if (barCtxElement) {
                        barCtxElement.style.height = '400px';  // Adjust height as needed
                        var barCtx = barCtxElement.getContext('2d');
                        new Chart(barCtx, barConfig);
                    }

                }
            });
            }

        }
    });
}

function createGauge(options) {
    // Verify if value is a valid number
    if (options.value === null || options.value === undefined || isNaN(options.value)) {
        const container = document.getElementById(options.id);
        if (container) {
            container.className = 'flex items-center justify-center h-64';
            container.innerHTML = '<p class="text-gray-500 italic">Pas de données disponibles</p>';
        }
        return;
    }

    new JustGage({
        id: options.id,
        value: options.value,
        min: options.min || 0,
        max: options.max,
        title: options.title,
        label: options.label,
        decimals: 1,
            gaugeWidthScale: 0.6,
            counter: true,
            pointer: true,
            pointerOptions: {
        toplength: -15,
        bottomlength: 10,
        bottomwidth: 12,
        color: '#8E8E93',
        stroke: '#fff',
        stroke_width: 3,
        stroke_linecap: 'round'
    },
        levelColors: ["#e62c2a", "#f46708", "#dfd419", "#7fd742", "#00a94c"],
            // Default options that don't need to be in config
            showMinMax: false,
            donut: false,
            relativeGaugeSize: true,
            // Font colors that don't need to be in config
            titleFontColor: "#333",
            valueFontColor: "#333",
            labelFontColor: "#666"
    });
}

function getBaseUrl() {
    const pathArray = window.location.pathname.split('/');
    pathArray.pop();
    return pathArray.join('/') + '/';
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
function createTree(container, taxonomyData) {
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

    const $tree = createList(taxonomyData);
    $(container).append($tree);
    openCurrentNode($tree, taxonId); // Ouvrez le noeud correspondant
}

function createImprovedTree(container, taxonomyData) {
    const baseUrl = getBaseUrl();
    const $treeContainer = $(container);
    const $searchInput = $('#taxonSearch');

    function createList(data, level = 0) {
        const $ul = $('<ul></ul>').addClass(`level-${level}`);
        $.each(data, function (i, item) {
            const $li = $('<li></li>');
            const $a = $('<a></a>', {
                'href': `${baseUrl}${item.id}.html`,
                'text': item.name,
                'data-id': item.id,
                'title': item.name // Ajout d'un titre pour améliorer l'accessibilité
            });

            if (item.id == taxonId) {
                $a.addClass('current-taxon');
            }

            if (item.children && item.children.length > 0) {
                const $span = $('<span class="toggle">▸</span>');
                const $childUl = createList(item.children, level + 1).hide();

                $span.on('click', function(event) {
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

    const $tree = createList(taxonomyData);
    $treeContainer.append($tree);
    openCurrentNode($tree, taxonId);
    scrollToCurrentTaxon();

    // Search functionality
    $searchInput.on('input', function() {
        const searchTerm = $(this).val().toLowerCase();
        $tree.find('li').each(function() {
            const $li = $(this);
            const taxonName = $li.find('> a').text().toLowerCase();
            if (taxonName.includes(searchTerm)) {
                $li.show();
                $li.parents('li').show();
                $li.find('ul').show();
            } else {
                $li.hide();
            }
        });
    });

    // Scroll to the current taxon
    function scrollToCurrentTaxon() {
        const $currentTaxon = $tree.find('.current-taxon');
        if ($currentTaxon.length) {
            const containerTop = $treeContainer.offset().top;
            const taxonTop = $currentTaxon.offset().top;
            const scrollPosition = taxonTop - containerTop - ($treeContainer.height() / 2) + ($currentTaxon.height() / 2);

            $treeContainer.scrollTop(Math.max(0, scrollPosition));
        }
    }
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
        const map = L.map('mapContainer', {
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

window.createTree = createImprovedTree;
window.loadCharts = loadCharts;
window.initMap = initMap;