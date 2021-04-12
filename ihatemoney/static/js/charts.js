function populateCharts(member_stats, months_in, monthly_stats) {

    var members = [];
    var total_per_member = ['CurrentBalance'];
    var total_exp_per_member = {};
    member_stats.forEach(function(stat) {
        var member_name = stat.member.name;
        members.push(member_name)
        var val = stat.balance;
        total_per_member.push(val);
        total_exp_per_member[member_name] = 0;
    });

        
    //Start of chart for total expenses per month
    var month_to_int = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
    };

    var months =[];
    var exp_per_month = [];
    //date_time is of form Sun, 11 Apr 2021 12:50:23 GMT

    months_in.forEach(function(date_time) {
        var month_year = monthYearStr(date_time);
        //  month_year is of form Apr 2021
        var year = parseInt(month_year.slice(4, 8));
        var month = month_year.slice(0,3);
        months.push(month_year);
        exp_per_month.push(monthly_stats[year][month_to_int[month]]);
    });
        
    months.reverse();
    exp_per_month.reverse()
    exp_per_month.splice(0,0,"Combined Monthly Expenses");
    

    var exp_per_month_chart = bb.generate({
        title: {
            text: "Combined Monthly Expenses"
        },
        data: {
            columns: [
                exp_per_month
            ],
            type: "line",
        },
        axis: {
            x: {
                type: "category",
                categories: months
            },
            y: {
                label: "Amount"
            }
        },
        bindto: "#combinedPerMonth"
    }); 

    // End of total expenses per month chart

    // Start of expenses per member per month chart
    var members_exp_by_month = [];
    member_stats.forEach(function(stat) {
        var month_dict = [];
        var month_amount = {};
        stat.monthly_exp.forEach(function(data) {
            // data is a tuple with a datetime object (Mon Year) at index 0 and amount at idx 1.
            month_dict.push({
                date: monthYearStr(data[0]),
                amount: data[1],
            });
            var date = monthYearStr(data[0]);
            month_amount[date] = data[1] ;
            total_exp_per_member[stat.member.name] += data[1];
        });
        month_dict.reverse();
        
        members_exp_by_month.push({
            name: stat.member.name,
            exp_by_month: month_dict,
            member_months: month_amount,
        });
    });


    var member_exp_dict = {};

    members_exp_by_month.forEach(function(member) {  
        // inserting the name of the member as the first element of the array, as per bb docs
        member_exp_dict[member.name] = [member.name];
    });

    var chart_columns = [];
    months.forEach(function(month) {
        members_exp_by_month.forEach(function(member) {  
            // If current member had expenses on current month
            if (month in member.member_months) {
                member_exp_dict[member.name].push(member.member_months[month]);
            } else {
                member_exp_dict[member.name].push(0);
            }
        });
    });
    // Pushing each individual member's expenses per month array into the chart array
    // chart array is what is given to bb.generate
    members_exp_by_month.forEach(function(member) {
        chart_columns.push(member_exp_dict[member.name]);
    });
    var members_exp_month_chart = bb.generate({
        title: {
            text: "Monthly Expenses Per Member"
        },
        data: {
            columns: chart_columns,
            type: "line"
        },
        axis: {
            x: {
                type: "category",
                categories: months,
            },
            y: {
                label: "Amounts"
            }
        },
        bindto: "#memberPerMonth"
    });
    
    //end of expenses per month per member

    // Start of Expenses Pie Chart
    pie_cols = [];
    members_exp_by_month.forEach(function(member) {
        var participant = member.name;
        var spent = total_exp_per_member[member.name];
        var exp_arr = [participant, spent];
        pie_cols.push(exp_arr);
    });

    var pie = bb.generate({
        data: {
            columns: pie_cols,
            type: "pie",
        },
        bindto: "#expPie"
    });

    // End of Expenses Pie Chart
}


function monthYearStr(date_time) {
    //date_time is of form Sun, 11 Apr 2021 12:50:23 GMT
    var start_date_idx = date_time.indexOf(',') + 2;
    var end_date_idx = date_time.indexOf(':') - 3;
    var date = date_time.slice(start_date_idx, end_date_idx);
    // date in the form 11 Apr 2021
    // date in the form 11 Apr 2021
    var month_start_idx = date.indexOf(' ') + 1;
    var month = date.slice(month_start_idx, month_start_idx + 3);
    var year_start_idx = date.lastIndexOf(' ') + 1;
    var year = parseInt(date.slice(year_start_idx, year_start_idx + 4));
    var month_year = month + ' ' + year.toString();
    // returns date in form Apr 2021
    return month_year;
}
