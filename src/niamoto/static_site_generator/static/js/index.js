function loadCharts(taxon) {
    
            // Make sure the frequencies object contains data for DBH

            var frequencies = taxon.frequencies;

            if (frequencies && frequencies.dbh) {
                // Data for DBH chart
                var dbhData = {
                    labels: Object.keys(frequencies.dbh),
                    datasets: [{
                        label: 'DBH',
                        data: Object.values(frequencies.dbh),
                        // Other chart options
                    }]
                };

                // Configuration for DBH chart
                var dbhConfig = {
                    type: 'bar', // or 'line', 'pie', etc.
                    data: dbhData,
                    options: {}
                };

                // Create DBH chart
                var dbhChart = new Chart(
                    document.getElementById('dbhChart'),
                    dbhConfig
                );
            }

            if (frequencies && frequencies.elevation) {
                var elevationData = {
                    labels: Object.keys(frequencies.elevation).reverse(),
                    datasets: [{
                        label: 'Elevation',
                        data: Object.values(frequencies.elevation).reverse(),
                        // Other chart options
                    }]
                };
            
                var elevationConfig = {
                    type: 'bar', // or 'line', 'pie', etc.
                    data: elevationData,
                    options: {
                        indexAxis: 'y',
                    }
                };
            
                var elevationChart = new Chart(
                    document.getElementById('elevationChart'),
                    elevationConfig
                );
            }

            if (frequencies && frequencies.rainfall) {
                var rainfallData = {
                    labels: Object.keys(frequencies.rainfall).reverse(),
                    datasets: [{
                        label: 'rainfall',
                        data: Object.values(frequencies.rainfall).reverse(),
                        // Other chart options
                    }]
                };
            
                var rainfallConfig = {
                    type: 'bar', // or 'line', 'pie', etc.
                    data: rainfallData,
                    options: {
                        indexAxis: 'y',
                    }
                };
            
                var rainfallChart = new Chart(
                    document.getElementById('rainfallChart'),
                    rainfallConfig
                );
            }

            var datasets = []; // Array to store datasets
            // Create a dataset for each entry in holdridge
            Object.keys(frequencies.holdridge).forEach(function(key, index) {
                var color = getColor(index); // Get a color based on the index
                datasets.push({
                    label: key, // Use the key as the label
                    data: [frequencies.holdridge[key]], // The value is in an array to match Chart.js structure
                    backgroundColor: color.background,
                    borderColor: color.border,
                    borderWidth: 1
                });
            });



            var ctxMilieuVie = document.getElementById('milieuVieChart').getContext('2d');
            var ctx = document.getElementById('milieuVieChart').getContext('2d');
            var milieuVieChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['Habitat'], // A single global label for the X axis
                    datasets: datasets
                },
                options: {
                    scales: {
                        x: { stacked: true },
                        y: { 
                            stacked: true,
                            ticks: {
                                beginAtZero: true,
                                callback: function(value) {
                                    return value + '%'; // Add the percentage sign
                                }
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true // Show the legend if necessary
                        }
                    }
                }
            });


            var ctxStrate = document.getElementById('strateChart').getContext('2d');
            var strateChart = new Chart(ctxStrate, {
                type: 'bar',
                data: {
                    labels: Object.keys(frequencies.strate), // Update with the labels from your data set
                    datasets: [{
                        label: 'Percentage of population (%)',
                        data: Object.values(frequencies.strate), // Update with the data from your data set
                        backgroundColor: [
                            'rgba(63, 191, 63, 0.7)',
                            'rgba(63, 191, 63, 0.7)',
                            'rgba(63, 191, 63, 0.7)',
                            'rgba(63, 191, 63, 0.7)'
                        ],
                        borderColor: [
                            'rgba(63, 191, 63, 1)',
                            'rgba(63, 191, 63, 1)',
                            'rgba(63, 191, 63, 1)',
                            'rgba(63, 191, 63, 1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    indexAxis: 'y', // Chart.js v3 uses 'indexAxis' for horizontal charts
                    scales: {
                        x: { // Utilisez 'x' au lieu de 'xAxes' pour Chart.js v3
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1
                            }
                        },
                        y: { // Utilisez 'y' au lieu de 'yAxes' pour Chart.js v3
                            // Configuration spécifique à l'axe Y, si nécessaire
                        }
                    },
                    plugins: {
                        datalabels: {
                            color: '#000',
                            anchor: 'end',
                            align: 'right',
                            formatter: function(value, context) {
                                return context.chart.data.labels[context.dataIndex];
                            }
                        }
                    }
                }
            });


            const labels = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
            const flowerData = Object.values(frequencies.Pheno_flower);
            const fruitData = Object.values(frequencies.pheno_fruit);

            const ctxPheno = document.getElementById('phenoChart').getContext('2d');
            const phenoChart = new Chart(ctxPheno, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Flower',
                        data: flowerData,
                        backgroundColor: 'rgba(255, 206, 86, 0.5)',
                        borderColor: 'rgba(255, 206, 86, 1)',
                        borderWidth: 1
                    }, {
                        label: 'Fruit',
                        data: fruitData,
                        backgroundColor: 'rgba(54, 162, 235, 0.5)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    scales: {
                        y: {
                            beginAtZero: true,
                            stacked: true
                        },
                        x: {
                            stacked: true
                        }
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: 'Phénologie'
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false
                        },
                        legend: {
                            display: true
                        }
                    }
                }
            });

            var heightMax = taxon.height_max; // Make sure this is properly handled by your template server
            createGauge('heightMaxGauge', heightMax, 40, "Maximum height", "meters");

            var dbhMax = taxon.dbh_max;
            createGauge('dbhMaxGauge', dbhMax, 500, "Maximum diameter (DBH)", "centimeters");
    
            var woodDensityAvg = taxon.wood_density_avg;
            createGauge('woodDensityAvgGauge', woodDensityAvg, 1.200, "Wood density", "g/cm³");
                
            var leafThicknessAvg = taxon.leaf_thickness_avg;
            createGauge('leafThicknessAvgGauge', leafThicknessAvg, 800, "Leaf thickness", "µm");

            var leafSlaAvgGauge = taxon.leaf_sla_avg;
            createGauge('leafSlaAvgGauge', leafSlaAvgGauge, 50, "Specific leaf area", "m2.kg-1");
                
            var leafAreaAvgGauge = taxon.leaf_area_avg;
            createGauge('leafAreaAvgGauge', leafAreaAvgGauge, 1500, "Leaf area", "cm2");

            var leafLdmcAvgGauge = taxon.leaf_ldmc_avg;
            createGauge('leafLdmcAvgGauge', leafLdmcAvgGauge, 800, "Leaf dry matter content", "mg.g-1");

            var barkThicknessAvgGauge = taxon.bark_thickness_avg;
            createGauge('barkThicknessAvgGauge', barkThicknessAvgGauge, 80, "Bark thickness", "mm");


            var totalOcc = taxon.occ_count;
            var umOcc = taxon.occ_um_count;
            var numOcc = totalOcc - umOcc;

            var ctx = document.getElementById('distributionSubstratChart').getContext('2d');
            var distributionSubstratChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Ultramafic (UM)', 'non-Ultramafic (NUM)'],
                    datasets: [{
                        data: [umOcc, numOcc],
                        backgroundColor: ['#f9e076', '#d4d4d4'],
                        hoverBackgroundColor: ['#f6d32b', '#a8a8a8']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    legend: {
                        position: 'bottom'
                    },
                    title: {
                        display: true,
                        text: 'Substrate distribution'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(tooltipItem, data) {
                                var label = data.labels[tooltipItem.index] || '';
                                var value = data.datasets[0].data[tooltipItem.index];
                                var total = data.datasets[0].data.reduce(function(previousValue, currentValue) {
                                    return previousValue + currentValue;
                                });
                                var percentage = ((value / total) * 100).toFixed(1) + '%';
                                return label + ': ' + percentage;
                            }
                        }
                    }
                }
            });

            var freq_max_value = taxon.freq_max; // Exemple de valeur pour 'freq_max'

            new JustGage({
                id: 'distributionGeoGauge', 
                value: freq_max_value,
                min: 0,
                max: 100, 
                title: "Distribution géographique",
                label: "Nombre de parcelles (%)",
                pointer: true,
                gaugeWidthScale: 0.6,
                counter: true,
                donut: true,
                relativeGaugeSize: true,
                customSectors: [{
                    color: "#ff0000",
                    lo: 0,
                    hi: 20
                }, {
                    color: "#f9c802",
                    lo: 20,
                    hi: 40
                }, {
                    color: "#a9d70b",
                    lo: 40,
                    hi: 60
                }, {
                    color: "#45e900",
                    lo: 60,
                    hi: 80
                }, {
                    color: "#029a02",
                    lo: 80,
                    hi: 100
                }]
            });
};

function createGauge(id, value, max, title, label) {
    new JustGage({
        id: id,
        value: value,
        min: 0,
        max: max,
        title: title,
        label: label,
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
            hi: max * 0.33
        }, {
            color: "#ffff00",
            lo: max * 0.33,
            hi: max * 0.66
        }, {
            color: "#00ff00",
            lo: max * 0.66,
            hi: max
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
                'text': item.name
            });

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
}

function initMap() {
    

    var geoPoints = taxon.geo_pts_pn;

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

    map.on('load', function() {
        document.getElementById('mapLoader').style.display = 'none';
    });
    

    // Ajouter les points géographiques pour le taxon
    if (geoPoints && geoPoints.coordinates) {
        geoPoints.coordinates.forEach(function (coord) {
            L.circle([coord[1], coord[0]], {
                color: '#1fb99d',      // The color of the circle's line
                fillColor: '#00716b',  // The fill color
                fillOpacity: 0.5,   // The fill transparency
                radius: 2000,         // The circle's radius in meters
                weight: 1         // The thickness of the circle's line
            }).addTo(map);
        });

        if (geoPoints.coordinates.length > 0) {
            map.fitBounds(geoPoints.coordinates.map(coord => [coord[1], coord[0]]));
        }
    }

}

// Function to get a color based on the index
function getColor(index) {
    var colors = [
        { background: 'rgba(54, 162, 235, 0.6)', border: 'rgba(54, 162, 235, 1)' },
        { background: 'rgba(75, 192, 192, 0.6)', border: 'rgba(75, 192, 192, 1)' },
        { background: 'rgba(255, 99, 132, 0.6)', border: 'rgba(255, 99, 132, 1)' }
        // Add more colors if necessary
    ];
    return colors[index % colors.length]; // Repeat colors if more keys than defined colors
}

window.createTree = createTree;
window.loadCharts = loadCharts;
window.initMap = initMap;