(function(){
  function debounce(fn, wait){
    let t; return function(){
      const ctx=this, args=arguments; clearTimeout(t);
      t=setTimeout(function(){ fn.apply(ctx,args); }, wait);
    };
  }

  function fetchJSON(url){
    return fetch(url, {credentials: 'same-origin'}).then(function(r){
      if(!r.ok) throw new Error('HTTP '+r.status);
      return r.json();
    });
  }

  function renderList(container, items, onSelect){
    container.innerHTML='';
    items.forEach(function(item){
      var el=document.createElement('div');
      el.className='school-autocomplete-item';
      var name=document.createElement('div');
      name.className='school-autocomplete-name';
      name.textContent=item.name || '';
      var addr=document.createElement('div');
      addr.className='school-autocomplete-address';
      addr.textContent=item.address || '';
      el.appendChild(name);
      el.appendChild(addr);
      el.dataset.id=item.id;
      el.addEventListener('click', function(){ onSelect(item); });
      container.appendChild(el);
    });
  }

  function setup(input){
    var apiUrl = input.getAttribute('data-api-url') || '/api/school';
    var hiddenId = input.getAttribute('data-hidden-input');
    var hidden = document.getElementById(hiddenId);
    var list = document.getElementById(input.id.replace(/_label$/, '_list'));

    function selectItem(item){
      hidden.value = item.id;
      input.value = item.name || '';
      list.innerHTML='';
    }

    var initialId = input.getAttribute('data-selected-id');
    if(initialId){
      fetchJSON(apiUrl.replace(/\/?$/, '/') + initialId)
        .then(function(data){ if(data && data.name){ input.value = data.name; }}).catch(function(){});
    }

    var doSearch = debounce(function(){
      var q = input.value.trim();
      if(q.length < 2){ list.innerHTML=''; return; }
      fetchJSON(apiUrl + '?q=' + encodeURIComponent(q))
        .then(function(items){ renderList(list, items, selectItem); })
        .catch(function(){ list.innerHTML=''; });
    }, 250);

    input.addEventListener('input', function(){
      hidden.value = '';
      doSearch();
    });

    var otherBtn = input.parentElement.querySelector('.school-autocomplete-other');
    if(otherBtn){
      otherBtn.addEventListener('click', function(){
        hidden.value = 'other';
        input.value = '';
        list.innerHTML='';
      });
    }

    document.addEventListener('click', function(e){
      if(!list.contains(e.target) && e.target !== input){ list.innerHTML=''; }
    });
  }

  function init(){
    document.querySelectorAll('input.school-autocomplete').forEach(setup);
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  }else{ init(); }
})();
