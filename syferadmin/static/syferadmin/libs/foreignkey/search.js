$(function(){
	initSelect2();
	$('.add-row a').on('click', function(e){
		setTimeout(function(){
			initSelect2();
		}, 500);
	});
});

function initSelect2() {
	$('[data-foreignkey_url]:visible').each(function(){
		var $this = $(this);
		if(!$this.is('.select2-initialized')) {
			$this.select2({
				ajax: {
					url: $this.data('foreignkey_url'),
					cache: true,
					dataType: 'json',
					delay: 150,
					type: 'GET',
					processResults: function(data, params){
						params.page = params.page || 1;
						return {
							results: $.map(data.results, function(item){
								return {
									text: $(item.display),
									id: item.pk,
									value: item.value,
								}
							}),
							pagination: {
								more: (params.page * 30) < data.count
							}
						}
					}
				},
				minimumInputLength: 2,
				templateSelection: function(data) {
					return data.value || data.text;
				},
				width: '500'
			}).addClass('.select2-initialized');
		}	
	});
}