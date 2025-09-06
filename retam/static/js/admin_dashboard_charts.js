document.addEventListener('DOMContentLoaded', function() {
    // Graphique 1: Paiements par mois
    const paymentsCtx = document.getElementById('paymentsChart');
    if (paymentsCtx) {
        const paymentsData = JSON.parse('{{ paiements_data|escapejs }}');
        new Chart(paymentsCtx, {
            type: 'line',
            data: {
                labels: paymentsData.map(item => item.mois),
                datasets: [{
                    label: 'Montant (FCFA)',
                    data: paymentsData.map(item => item.total),
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    fill: true,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.parsed.y.toLocaleString() + ' FCFA';
                            }
                        }
                    }
                }
            }
        });
    }

    // Graphique 2: Types de contribuables
    const typesCtx = document.getElementById('typesChart');
    if (typesCtx) {
        const typesData = JSON.parse('{{ types_data|escapejs }}');
        new Chart(typesCtx, {
            type: 'doughnut',
            data: {
                labels: typesData.map(item => item.type),
                datasets: [{
                    data: typesData.map(item => item.count),
                    backgroundColor: [
                        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                        '#9966FF', '#FF9F40', '#8AC249', '#EA5545'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'right',
                    }
                }
            }
        });
    }

    // Graphique 3: Zones géographiques
    const zonesCtx = document.getElementById('zonesChart');
    if (zonesCtx) {
        const zonesData = JSON.parse('{{ zones_data|escapejs }}');
        new Chart(zonesCtx, {
            type: 'bar',
            data: {
                labels: zonesData.map(item => item.zone),
                datasets: [{
                    label: 'Nombre de contribuables',
                    data: zonesData.map(item => item.count),
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgb(54, 162, 235)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    }
});