document.addEventListener('DOMContentLoaded', function() {
    // Initialisation des graphiques
    const ctx = document.getElementById('myChart');
    if (ctx) {
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Red', 'Blue', 'Yellow'],
                datasets: [{
                    label: '# of Votes',
                    data: [12, 19, 3],
                    borderWidth: 1
                }]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
});