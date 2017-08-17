$(function(){
	$('[data-text-alignment-widget]').each(function(){
		var $this = $(this),
			wrapper = $this.parent(),
			table = $('<table class="text-alignment-widget"><tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr></table>');
		table.on('click', 'td', function(e){
			var tbl = $(this).closest('table');
			tbl.find('td').removeClass('active');
			$(this).addClass('active');
			$this.val($(this).data('value'));
			$this.trigger('chosen:updated');
		});
		var count = 0;
		$this.find('option').each(function(){
			if($(this).val()) {
				table.find('td').eq(count).attr('data-value', $(this).val()).text($(this).text());
				count++;
			}
		});
		table.find('[data-value="' + $this.val() + '"]').trigger('click');

		$this.after(table);
		table.siblings().not('label').hide();
	});
});