 // Utility to select all or none of the checkboxes in the add_bill form.
function selectCheckboxes(value){
  var els = document.getElementsByName('payed_for');
  for(var i = 0; i < els.length; i++){
    els[i].checked = value;
  }
}

function updateCheckBoxesFromPrivacySelect() {
  var history_checkbox = document.getElementById('logging_enabled');
  var record_ip_checkbox = document.getElementById('record_ip');
  var record_ip_checkbox_text = document.getElementById("record_ip_label");
  var select_input = document.getElementById("logging_preferences");

  if (select_input.selectedIndex === 0) {
    history_checkbox.checked = false;
    record_ip_checkbox.checked = false;
    record_ip_checkbox.disabled = true;
    record_ip_checkbox_text.classList.add("text-muted");
  } else if (select_input.selectedIndex === 1 || select_input.selectedIndex === 2) {
    history_checkbox.checked = true;
    record_ip_checkbox.disabled = false;
    record_ip_checkbox_text.classList.remove("text-muted");
    if (select_input.selectedIndex === 2) {
      record_ip_checkbox.checked = true
    }
  }
}

function updatePrivacySelectFromCheckBoxes() {
  var history_checkbox = document.getElementById('logging_enabled');
  var record_ip_checkbox = document.getElementById('record_ip');
  var record_ip_checkbox_text = document.getElementById("record_ip_label");
  var select_input = document.getElementById("logging_preferences");

  if (!history_checkbox.checked) {
    record_ip_checkbox.checked = false;
    record_ip_checkbox.disabled = true;
    record_ip_checkbox_text.classList.add("text-muted");
    select_input.selectedIndex = 0
  } else {
    record_ip_checkbox.disabled = false;
    record_ip_checkbox_text.classList.remove("text-muted");
    if (record_ip_checkbox.checked){
      select_input.selectedIndex = 2
    } else {
      select_input.selectedIndex = 1
    }
  }
}