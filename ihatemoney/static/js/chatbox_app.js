const chatButton = document.querySelector('.chatbox__button');
const chatContent = document.querySelector('.chatbox__support');
const icons = {
    isClicked: '<img src="https://img.icons8.com/material-rounded/24/000000/chat--v2.png"/>',
    isNotClicked: '<img src="https://img.icons8.com/material-rounded/40/000000/chat--v2.png"/> '
}
const chatbox = new InteractiveChatbox(chatButton, chatContent, icons);
chatbox.display();
chatbox.toggleIcon(false, chatButton);