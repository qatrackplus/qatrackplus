
function rgbaStringToArray(rgba) {
    rgba = rgba.match(/^rgb[a]?\((\d+),\s*(\d+),\s*(\d+)(,\s*(0(\.[0-9][0-9]+?)?|1))?\)$/);
    var a = rgba[5] ? parseFloat(rgba[5]) : 1;
    return [parseInt(rgba[1]), parseInt(rgba[2]), parseInt(rgba[3]), a];
}

/**
 * Calculates the brightness of the rgba value assuming against a white surface. Returns true if white text would
 * not be appropriate on this colour.
 *
 * @param rgba
 * @returns {boolean}
 */
function isTooBright(rgba) {
    var o = Math.round(((parseInt(rgba[0]) * 299) + (parseInt(rgba[1]) * 587) + (parseInt(rgba[2]) * 114)) / 1000);
    return o + (255 - o) * (1 - rgba[3]) > 140;
}

var lightenDarkenColor = function (col, amt) {

    amt = parseInt(amt);
	var r = col[0] + amt;
	if (r > 255) {
		r = 255;
	} else if (r < 0) {
		r = 0;
	}
	var b = col[1] + amt;
	if (b > 255) {
		b = 255;
	} else if (b < 0) {
		b = 0;
	}
	var g = col[2] + amt;
	if (g > 255) {
		g = 255;
	} else if (g < 0) {
		g = 0;
	}
    var a = col[3] - amt/100;
    if (a > 1) a = 1;
    else if (a < 0) a = 0;
	return 'rgba(' + r + ',' + b + ',' + g + ',' + a + ')';
};

function apply_data_colour($elem) {
	var bg_colour = $elem.attr('data-bgcolour');
	var colour = $elem.attr('data-colour');
	if (bg_colour != null) {
		$elem.css('background-color', bg_colour);
		$elem.css('border-color', bg_colour);
		if (isTooBright(rgbaStringToArray($elem.css('background-color')))) {
			$elem.css('color', 'black').children().css('color', 'black');
		}
		else {
			$elem.css('color', 'white').children().css('color', 'white');
		}
	}
	if (colour != null) {
		$elem.css('color', colour);
	}
}