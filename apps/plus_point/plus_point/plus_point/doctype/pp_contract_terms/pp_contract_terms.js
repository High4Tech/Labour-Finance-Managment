frappe.ui.form.on('PP Contract Terms', {
    refresh(frm) {
        if (frm.is_new()) return;
        frm.add_custom_button(__('Project finances'), async () => {
            const result = await frappe.db.get_value('Project', frm.doc.project, 'company');
            frappe.set_route('query-report', 'PLUS POINT Project Finances', {project: frm.doc.project, company: result.message.company});
        });
        if (frm.doc.status === 'Active') frm.add_custom_button(__('Prepare client invoice'), async () => {
            const rpc=plus_point.setup_rpc,options=await rpc('plus_point.billing.invoice_options',{contract_terms:frm.doc.name});
            let sequence=0,manual=false,setting=false,busy=false;
            const dialog=new frappe.ui.Dialog({title:__('Prepare draft invoice'),fields:[
                {fieldname:'invoice_error',fieldtype:'HTML'},
                {fieldname: 'item_code', fieldtype: 'Link', options: 'Item',only_select:1, label: __('Service item'), description:__('Required to create the invoice.'),get_query:()=>({filters:{is_stock_item:0,disabled:0}})},
                {fieldname:'invoice_currency',fieldtype:'Link',options:'Currency',only_select:1,label:__('Client invoice currency'),default:options.currency},
                {fieldname:'exchange_rate',fieldtype:'Float',label:__('Accounting currency per invoice unit ({0})',[options.base_currency]),precision:9},
                {fieldname:'rate_info',fieldtype:'HTML'},
                {fieldname: 'from_date', fieldtype: 'Date', label: __('From date')},
                {fieldname: 'to_date', fieldtype: 'Date', label: __('To date')}
            ],primary_action_label:__('Create draft invoice'),async primary_action(){
                const values=dialog.get_values(true)||{};if(busy)return;
                if(!values.item_code||!values.invoice_currency||!Number.isFinite(Number(values.exchange_rate))||!(Number(values.exchange_rate)>0)){failure(__('Choose a service item, currency and positive exchange rate.'));return;}
                failure('');busy=true;ready();try{const result=await rpc('plus_point.billing.create_invoice',{...values,contract_terms:frm.doc.name});dialog.hide();frappe.set_route('Form','Sales Invoice',result.name);}catch(error){failure(error.message);}finally{busy=false;ready();}
            }});
            function info(text){dialog.fields_dict.rate_info.$wrapper.empty().append($('<p role="status"></p>').text(text));}
            function failure(text){const box=dialog.fields_dict.invoice_error.$wrapper.empty();if(text)box.append($('<p class="text-danger" role="alert" tabindex="-1"></p>').text(text)).find('p').trigger('focus');}
            function ready(){dialog.get_primary_btn().prop('disabled',busy||!(Number(dialog.get_value('exchange_rate'))>0));}
            async function refresh(){const own=++sequence;manual=false;setting=true;try{await dialog.set_value('exchange_rate','');}finally{setting=false;}ready();const currency=dialog.get_value('invoice_currency');dialog.set_df_property('exchange_rate','read_only',currency===options.base_currency?1:0);if(!currency)return;info(__('Getting the latest published rate…'));
                try{const quote=await rpc('plus_point.billing.quote',{company:options.company,currency});if(own!==sequence)return;
                    if(!manual){setting=true;try{await dialog.set_value('exchange_rate',Number(quote.rate));}finally{setting=false;}}
                    if(!manual)info(__('1 {0} = {1} {2}. You can enter an agreed rate. {3}',[currency,quote.rate,options.base_currency,quote.as_of?new Date(quote.as_of*1000).toLocaleDateString():'']));
                }catch(error){if(own===sequence)info(__('Could not load the current rate. Enter the agreed exchange rate to continue.'));}finally{ready();}
            }
            dialog.show();plus_point.enhance_selectors(dialog);
            dialog.fields_dict.invoice_currency.df.onchange=refresh;
            dialog.fields_dict.exchange_rate.df.onchange=()=>{if(!setting){manual=true;info(__('Agreed rate: 1 {0} = {1} {2}.',[dialog.get_value('invoice_currency'),dialog.get_value('exchange_rate'),options.base_currency]));}ready();};
            dialog.fields_dict.exchange_rate.$input.on('input',()=>{manual=true;});
            await refresh();
        });
    }
});
