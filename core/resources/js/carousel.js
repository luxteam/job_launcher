function openCarousel(caseName) {
    let carouselName = 'carouselPopup_' + caseName

    openModalWindow(carouselName)
    initCarousel()
}


function changeActiveThumbnail(element, number) {
    $('#carousel').carousel(number);
    $('[id^=carouselThumbnail-]').removeClass('selected');
    $(element).addClass('selected');
}


function initCarousel() {
    $('#carousel').carousel({
        interval: 5000
    });

    $('#carousel').on('slid.bs.carousel', function (e) {
        let id = $('.item.active').data('slide-number');
        id = parseInt(id);
        $('[id^=carouselThumbnail-]').removeClass('selected');
        $('[id=carouselThumbnail-' + id + ']').addClass('selected');
    });
}
