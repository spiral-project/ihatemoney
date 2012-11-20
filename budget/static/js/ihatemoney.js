 // Add scripts to select all or non of the checkboxes in the add_bill form
function selectall()
    {
        var els = document.getElementsByName('payed_for');
        for(var i =0;i<els.length;i++)
        {
            els[i].checked=true;
        }
    }
function selectnone()
    {
        var els = document.getElementsByName('payed_for');
        for(var i =0;i<els.length;i++)
        {
            els[i].checked=false;
        }
    }

