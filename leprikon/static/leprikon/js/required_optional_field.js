$('.required-optional-field').each(function () {
    var requireOptionalField = $(this);
    var choiceInput = requireOptionalField.find('.required-optional-field-choice input');
    var valueBlock = requireOptionalField.find('.required-optional-field-value');
    var valueInput = valueBlock.find('input');
    choiceInput.change(function () {
        if (requireOptionalField.find('.required-optional-field-choice input:checked').val() === 'value') {
            valueBlock.removeClass('hidden');
        } else {
            valueBlock.addClass('hidden');
        }
    }).change();

    var hiddenInput = requireOptionalField.find('.required-optional-field-input');
    var choiceInputEmpty = requireOptionalField.find('.required-optional-field-choice input[value="empty"]');
    var choiceInputValue = requireOptionalField.find('.required-optional-field-choice input[value="value"]');
    var choiceInputEmptyId = choiceInputEmpty.attr('id');
    var choiceInputEmptyLabel = requireOptionalField.find(`label[for="${choiceInputEmptyId}"]`).text();
    hiddenInput.change(function() {
        if (this.value === '') {
            choiceInput.prop('checked', false);
            valueInput.val('').change();
            valueBlock.addClass('hidden');
        } else if (this.value === choiceInputEmptyLabel) {
            choiceInputEmpty.click();
            valueInput.val('').change();
        } else {
            choiceInputValue.click();
            valueInput.val(this.value).change();
        }
    });
});
