function page_fade_in() {
    document.body.className = 'visible';
}

function check_pw() {
  if (document.getElementById('password').value == document.getElementById('confirm_password').value) {
    document.getElementById('submit').disabled = false;
    document.getElementById('password').style.backgroundColor = 'green';
    document.getElementById('confirm_password').style.backgroundColor = 'green';
  } else {
    document.getElementById('submit').disabled = true;
    document.getElementById('password').style.backgroundColor = 'red';
    document.getElementById('confirm_password').style.backgroundColor = 'red';
  }
}
