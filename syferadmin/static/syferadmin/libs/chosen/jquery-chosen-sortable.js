/*
 * Author: Yves Van Broekhoven & Simon Menke
 * Created at: 2012-07-05
 *
 * Requirements:
 * - jQuery
 * - jQuery UI
 * - Chosen
 *
 * Version: 1.0.0
 */
(function($) {

  $.fn.chosenOrder = function() {
    var $this   = this.filter('[multiple]').first(),
        $chosen = $this.siblings('.chosen-container');

    return $($chosen.find('.chosen-choices li[class!="search-field"]').map( function() {
      if (!this) {
        return undefined;
      }
      var text = $(this).text(),
          found = undefined;
      $this.find('option:contains(' + text + ')').each(function(){
        if ($(this).text() == text) found = this;
      });
      return found;
    }));
  };


  /*
   * Extend jQuery
   */
  $.fn.chosenSortable = function(){
    var $this = this.filter('[multiple]');

    $this.each(function(){
      var $select = $(this);
      var $chosen = $select.siblings('.chosen-container');

      // On mousedown of choice element,
      // we don't want to display the dropdown list
      $chosen.find('.chosen-choices').bind('mousedown', function(event){
        if ($(event.target).is('span')) {
          event.stopPropagation();
        }
      });

      // Initialize jQuery UI Sortable
      $chosen.find('.chosen-choices').sortable({
        'placeholder' : 'placeholder',
        'items'       : 'li:not(.search-field)',
        //'update'      : _update,
        'tolerance'   : 'pointer'
      });

      // Intercept form submit & order the chosens
      $select.closest('form').on('submit', function(){
        var $options = $select.chosenOrder();
        $select.children().remove();
        $select.append($options);
      });

    });

    return $this;

  };

}(jQuery));