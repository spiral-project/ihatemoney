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

// Automatically hide and show the default value of a text field
// handly in order to write user information in the text field.
// jquery selector should return only one text field.
    var auto_hide_default_text = function(text_field_selector){
        // record the text in the text field before the first text field focus
        var default_text;
        
        var hide_text = function(){
            if(default_text==undefined){
                default_text=this.value;
                this.value="";
            }
            else if(this.value==default_text){
                this.value="";
            }
        }

        var show_text = function(){
            if(this.value==""){
                this.value=default_text;
            }
        }
        
        var field = $(text_field_selector);
        field.focus(hide_text);
        field.blur(show_text);
    }