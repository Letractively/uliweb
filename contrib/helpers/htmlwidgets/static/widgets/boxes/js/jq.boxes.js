(function($){
	$.fn.boxes = function(){
		return this.each(function(){
			var t = $(this);
			t.wrap('<div class="cssbox"><div class="c1"><div class="c2"></div></div><div class="c3"></div></div>');
		});
	};
})(jQuery);