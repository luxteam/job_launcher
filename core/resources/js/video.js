function clickOnVideo(element) {

    if (element.requestFullscreen) {
        element.requestFullscreen();
    } else if (element.mozRequestFullScreen) {
        element.mozRequestFullScreen();
    } else if (element.webkitRequestFullscreen) {
        element.webkitRequestFullscreen();
    }
}


document.addEventListener("fullscreenchange", function (event) {

    let element = event.target

    if (document.fullscreenElement) {
        element.setAttribute("controls", "")
        element.play()
    } else {
        element.removeAttribute("controls")
        element.pause()
    }

});