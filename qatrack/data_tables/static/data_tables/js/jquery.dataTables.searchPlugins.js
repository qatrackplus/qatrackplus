jQuery.fn.dataTableExt.oApi.fnFilterOnReturn = function (oSettings) {
    var _that = this;
  
    this.each(function (i) {
        $.fn.dataTableExt.iApiIndex = i;
        var $this = this;
        var anControl = $('input.text_filter');//, _that.fnSettings().aanFeatures.f);
        anControl.unbind('keyup').bind('keypress', function (e) {
            if (e.which == 13) {
                $.fn.dataTableExt.iApiIndex = i;
                _that.fnFilter(anControl.val());
            }
        });
        return this;
    });
    return this;
};

jQuery.fn.dataTableExt.oApi.fnSetFilteringDelay = function ( oSettings, iDelay ) {
    var _that = this;
 
    if ( iDelay === undefined ) {
        iDelay = 1000;
    }
      
    this.each( function ( i ) {
        $.fn.dataTableExt.iApiIndex = i;
        var
            $this = this,
            oTimerId = null,
            sPreviousSearch = null,
            anControl = $( 'input.text_filter');//, _that.fnSettings().aanFeatures.f );
          
            anControl.unbind( 'keyup' ).bind( 'keyup', function() {
                var $$this = $this;
                var ctrl = $(this);    
                if (sPreviousSearch === null || sPreviousSearch != ctrl.val()) {
                    window.clearTimeout(oTimerId);
                    sPreviousSearch = ctrl.val(); 
                    oTimerId = window.setTimeout(function() {
                        $.fn.dataTableExt.iApiIndex = i;
                        _that.fnFilter( ctrl.val() );
                    }, iDelay);
                }
            });
          
        return this;
    } );
    return this;
};