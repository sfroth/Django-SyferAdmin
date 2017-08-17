// Currency conversion functions
var currency = '\$';

// String to cents
String.prototype.toCents = function () {
	cents = parseInt(this.replace(/\D/g, ""));
	if (isNaN(cents)) cents = 0;
   periodPos = this.length - this.indexOf(".") - 1
   if (this.indexOf(".") < 0) cents *= 100;
   else if (periodPos < 2) cents *= 10;
   if (this.indexOf("-") != -1) cents = -cents;
   return cents;
};
// String to currency (delegates to Number)
String.prototype.currency = function() {
	return parseInt(this).currency();
};
// Number to currency format
Number.prototype.currency = function() {
	return this.toMoney(currency, 2);
}
// Jquery shortcut
$.fn.currency = function(amount) {
   $(this).each(function() {
		currencyAmount = new Number(amount / 100);
      $(this).text(currencyAmount.toMoney(currency, 2));
	});
	return $(this);
};

/**
 Money formatting
 */
Number.prototype.toMoney = function(currency, decimals, decimal_sep, thousands_sep)
{
   var n = this,
   c = isNaN(decimals) ? 2 : Math.abs(decimals), //if decimal is zero we must take it, it means user does not want to show any decimal
   d = decimal_sep || '.', //if no decimal separator is passed we use the dot as default decimal separator (we MUST use a decimal separator)

   /*
   according to [http://stackoverflow.com/questions/411352/how-best-to-determine-if-an-argument-is-not-sent-to-the-javascript-function]
   the fastest way to check for not defined parameter is to use typeof value === 'undefined'
   rather than doing value === undefined.
   */
   t = (typeof thousands_sep === 'undefined') ? ',' : thousands_sep, //if you don't want to use a thousands separator you can pass empty string as thousands_sep value

   sign = (n < 0) ? '-' : '',

   //extracting the absolute value of the integer part of the number and converting to string
   i = parseInt(n = Math.abs(n).toFixed(c)) + '',

   j = ((j = i.length) > 3) ? j % 3 : 0;
   return sign + currency + (j ? i.substr(0, j) + t : '') + i.substr(j).replace(/(\d{3})(?=\d)/g, "$1" + t) + (c ? d + Math.abs(n - i).toFixed(c).slice(2) : '');
}
Number.prototype.centsToMoney = function(currency, decimals, decimal_sep, thousands_sep) {
   return (this / 100).toMoney(currency, decimals, decimal_sep, thousands_sep)
}