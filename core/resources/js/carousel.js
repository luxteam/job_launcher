function openCarousel(caseName) {
    let carouselName = 'carouselPopup_' + caseName

    openModalWindow(carouselName)
    initCarousel(caseName)
}


function changeActiveThumbnail(element, caseName, number) {
    $(`#carousel_${caseName}`).carousel(number)
    $(`[id^=carouselThumbnail-${caseName}-]`).removeClass('selected')
    $(element).addClass('selected')
}


function initCarousel(caseName) {
    $(`[id^=carouselThumbnailImg-${caseName}-]`).each(function() {
        $(this).attr("src", $(this).attr("data-src"));
        $(this).removeAttr("data-src");
        console.log($(this)[0].outerHTML);
    });

    $(`[id^=carouselImg-${caseName}-]`).each(function() {
        $(this).attr("src", $(this).attr("data-src"));
        $(this).removeAttr("data-src");
        console.log($(this)[0].outerHTML);
    });

    $('#carousel_' + caseName).carousel({
        interval: false
    });

    $('#carousel_' + caseName).on('slid.bs.carousel', function (e) {
        let id = $('#carousel_' + caseName).find('.item.active').data('slide-number')
        id = parseInt(id)
        $(`[id^=carouselThumbnail-${caseName}-]`).removeClass('selected')
        let newActiveElement = $(`#carouselThumbnail-${caseName}-${id}`)
        newActiveElement.addClass('selected')
        newActiveElement[0].scrollIntoView()
    });
}
