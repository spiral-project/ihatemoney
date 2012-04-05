 // Add a script to select all or non of the checkboxes in the add_bill form
    function toggle()
    {
        var els = document.getElementsByName('payed_for');
        for(var i =0;i<els.length;i++)
        {
            if(document.getElementById('toggleField').checked)
            {
                els[i].checked=true;
            }
            else
            {
                els[i].checked=false;
            }
        }
    }

