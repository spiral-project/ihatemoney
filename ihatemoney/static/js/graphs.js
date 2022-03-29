function createGraphs(members_stats, monthly_stats) {
    let names = [];
    let balance = [];
    let colors = [];
    for (let i = 0; i < members_stats.length; i++) {
        names = names.concat(members_stats[i].member.name)
        balance = balance.concat(members_stats[i].balance)
        if(members_stats[i].balance < 0){
            colors = colors.concat('rgba(255, 0, 0, .5)')
        }
        else{
            colors = colors.concat('rgba(0, 128, 0, .5)')
        }
    }

    let spent = [];
    let month = [];
    for (const [year, month1] of Object.entries(monthly_stats)) {
        for (const [month2, value] of Object.entries(month1)) {
            spent = spent.concat(value);
            month = month.concat(month2);
        }
    }
    month = month.slice(-12);
    spent = spent.slice(-12);
    for (let i = 0; i < month.length; i++) {
        if(month[i] == 1){
            month[i] = 'Jan';
        }
        else if(month[i] == 2){
            month[i] = 'Feb';
        }
        else if(month[i] == 3){
            month[i] = 'Mar';
        }
        else if(month[i] == 4){
            month[i] = 'Apr';
        }
        else if(month[i] == 5){
            month[i] = 'May';
        }
        else if(month[i] == 6){
            month[i] = 'June';
        }
        else if(month[i] == 7){
            month[i] = 'July';
        }
        else if(month[i] == 8){
            month[i] = 'Aug';
        }
        else if(month[i] == 9){
            month[i] = 'Sept';
        }
        else if(month[i] == 10){
            month[i] = 'Oct';
        }
        else if(month[i] == 11){
            month[i] = 'Nov';
        }
        else if(month[i] == 12){
            month[i] = 'Dec';
        }
    }


    const ctx = document.getElementById('balance').getContext('2d');
    const myChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: names,
            datasets: [{
                label: '',
                data: balance,
                backgroundColor: colors,
                borderColor: colors,
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true
                }
            },
            title: {
                display: true,
                text: 'Balance',
                fontSize: 25,
                fontColor: 'rgb(0,0,0)'
            },
            legend:{
                display: false
            },
            scales: {
                xAxes: [{
                    ticks: {
                        fontSize: 15
                    }
                }]
            },
            responsive: false

        }
    });

    const chart2 = document.getElementById('monthlySpending').getContext('2d');
    const myChart2 = new Chart(chart2, {
        type: 'line',
        data: {
            labels: month,
            datasets: [{
                label: '',
                data: spent, 
                fill: false, 
                lineTension: .1,
                borderColor: 'rgb(128,128,128)'
            }]
        },
        options: {
            title: {
                display: true,
                text: 'Expenses Per Month in the Past Year',
                fontSize: 25,
                fontColor: 'rgb(0,0,0)'
            },
            legend:{
                display: false
            },
            responsive: false
        }
    });
}
