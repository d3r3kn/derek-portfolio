/* Scroll motion: blocks fade up as they come into view, charts draw themselves in,
   and headline numbers count up. Runs once per block. Does nothing when the visitor's
   device asks for reduced motion, and the page reads the same without it. */
(function(){
  if(!('IntersectionObserver' in window)||!Element.prototype.animate)return;
  if(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  document.documentElement.classList.add('motion');

  var BLOCKS='.hub a,.ex-card,.role,.grid figure,.note,.empty,.card,.kpis,.verified,.srcbox,.pipe,.checks,'+
             '.offer,.step,.promises,.about,.form-wrap,.resume-section';
  var CHARTS='.card,.kpis,.ex-stats';
  var NUMBERS='.k-value,.ex-stat b';
  var EASE='cubic-bezier(.2,.7,.2,1)';

  function charts(root){
    var list=root.matches(CHARTS)?[root]:[];
    root.querySelectorAll(CHARTS).forEach(function(c){list.push(c);});
    list.forEach(function(c){whenFilled(c,function(){draw(c);count(c);});});
  }

  // wait for content that the page fills in after loading its data
  function whenFilled(c,fn){
    if(filled(c)){fn();return;}
    var mo=new MutationObserver(function(){if(filled(c)){mo.disconnect();setTimeout(fn,30);}});
    mo.observe(c,{childList:true,subtree:true,characterData:true});
    setTimeout(function(){mo.disconnect();},8000);
  }
  function filled(c){
    if(c.querySelector('svg polyline,svg line,svg circle,.bar,.cb,.seg-s,.k-value'))return true;
    var b=c.querySelector(NUMBERS);return !!(b&&/\d/.test(b.textContent));
  }

  // 3. charts draw in, left to right
  function draw(c){
    c.querySelectorAll('svg').forEach(function(svg){
      var w=svg.getBoundingClientRect().width||1,left=svg.getBoundingClientRect().left;
      svg.querySelectorAll('polyline,line,path').forEach(function(s){
        var cs=getComputedStyle(s);
        if(cs.stroke==='none'||parseFloat(cs.strokeWidth)<1.4||cs.visibility==='hidden')return;
        if(s.getAttribute('stroke-dasharray')||cs.strokeDasharray!=='none')return;
        if(s.closest('marker'))return;
        var len=s.getTotalLength?s.getTotalLength():0;if(len<2)return;
        var x=(s.getBoundingClientRect().left-left)/w,delay=Math.max(0,Math.min(1,x))*700;
        s.style.strokeDasharray=len;
        s.animate([{strokeDashoffset:len},{strokeDashoffset:0}],{duration:s.tagName==='line'?380:1100,delay:delay,easing:EASE,fill:'backwards'})
         .finished.then(function(){s.style.strokeDasharray='';},function(){s.style.strokeDasharray='';});
      });
      svg.querySelectorAll('circle,polygon').forEach(function(s){
        if(getComputedStyle(s).visibility==='hidden'||s.getAttribute('fill')==='transparent')return;
        var x=(s.getBoundingClientRect().left-left)/w;
        s.animate([{opacity:0},{opacity:1}],{duration:400,delay:s.tagName==='polygon'?250:200+Math.max(0,Math.min(1,x))*700,fill:'backwards'});
      });
    });
    c.querySelectorAll('.bar,.seg-s').forEach(function(b,i){
      b.style.transformOrigin='left center';
      b.animate([{transform:'scaleX(0)'},{transform:'scaleX(1)'}],{duration:700,delay:Math.min(i,20)*35,easing:EASE,fill:'backwards'});
    });
    c.querySelectorAll('.cb').forEach(function(b,i){
      b.style.transformOrigin='center bottom';
      b.animate([{transform:'scaleY(0)'},{transform:'scaleY(1)'}],{duration:700,delay:i*70,easing:EASE,fill:'backwards'});
    });
    c.querySelectorAll('.heat td').forEach(function(td,i){
      td.animate([{opacity:0},{opacity:1}],{duration:350,delay:Math.min(i,120)*6,fill:'backwards'});
    });
  }

  // 4. numbers count up to their exact published value
  function count(c){c.querySelectorAll(NUMBERS).forEach(countUp);}
  function countUp(el){
    var final=el.textContent,re=/\d[\d,]*(?:\.\d+)?/g;
    if(!re.test(final)||final.indexOf('→')>-1)return;   // skip "before → after" pairs
    var parts=[];final.replace(re,function(m){parts.push(m);return m;});
    var t0=null,dur=900,last=final;
    function fmt(m,t){
      var dec=(m.split('.')[1]||'').length,v=parseFloat(m.replace(/,/g,''))*t;
      var s=v.toFixed(dec);
      if(m.indexOf(',')>-1){var p=s.split('.');p[0]=p[0].replace(/\B(?=(\d{3})+(?!\d))/g,',');s=p.join('.');}
      return s;
    }
    function frame(ts){
      if(el.textContent!==last)return;            // the page changed it (a filter): stop
      if(t0===null)t0=ts;
      var k=Math.min(1,(ts-t0)/dur),e=1-Math.pow(1-k,3),i=0;
      last=k<1?final.replace(re,function(m){return fmt(parts[i++],e);}):final;
      el.textContent=last;
      if(k<1)requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  // 1. blocks fade up once, a few siblings at a time
  var io=new IntersectionObserver(function(entries){
    entries.forEach(function(en){
      if(!en.isIntersecting)return;
      var el=en.target;io.unobserve(el);
      var sib=el.parentNode?[].indexOf.call(el.parentNode.children,el):0;
      el.style.transitionDelay=Math.min(sib,4)*70+'ms';
      el.classList.add('in');
      setTimeout(function(){el.style.transitionDelay='';},900);   // keep hover effects instant
      charts(el);
    });
  },{rootMargin:'0px 0px -8% 0px',threshold:.08});

  function init(){
    var seen=[];
    document.querySelectorAll(BLOCKS).forEach(function(el){
      if(el.closest('.rv'))return;                    // reveal only the outer block
      el.classList.add('rv');seen.push(el);
    });
    seen.forEach(function(el){io.observe(el);});
    // number tiles outside any revealed block
    document.querySelectorAll('.ex-stats').forEach(function(s){if(!s.closest('.rv'))io.observe(s);});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
