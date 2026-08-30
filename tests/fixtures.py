LISTING_PAGE = b"""
<html><head><title>Search - Workplace Relations Commission</title></head><body>
<div class="results-header"><p>3 results</p></div>
<ul>
  <li class="each-item clearfix">
    <div class="row">
      <h2 class="title" title="ADJ-00047352"><a href="/en/cases/2024/february/adj-00047352.html">ADJ-00047352</a></h2>
      <span class="date">31/01/2024</span>
    </div>
    <p class="description" title="Car Valet V Motor Garage">Car Valet V Motor Garage</p>
    <div class="row bottom-ref"><span>Ref no:</span><span class="refNO">ADJ-00047352</span></div>
  </li>
  <li class="each-item clearfix">
    <div class="row">
      <h2 class="title" title="IR - SC - 00001785"><a href="/en/cases/2024/january/ir-sc-00001785.html">IR - SC - 00001785</a></h2>
      <span class="date">30/01/2024</span>
    </div>
    <p class="description" title="A Worker V A Company">A Worker V A Company</p>
    <div class="row bottom-ref"><span>Ref no:</span><span class="refNO">IR - SC - 00001785</span></div>
  </li>
  <li class="each-item clearfix">
    <div class="row">
      <h2 class="title" title="ADJ-00035852"><a href="/en/cases/2024/january/adj-00035852.html">ADJ-00035852</a></h2>
      <span class="date">15/01/2024</span>
    </div>
    <p class="description" title="A Driver v A Logistics Company">A Driver v A Logistics Company</p>
    <div class="row bottom-ref"><span>Ref no:</span><span class="refNO">ADJ-00035852</span></div>
  </li>
</ul>
</body></html>
"""

EMPTY_LISTING_PAGE = b"""
<html><head><title>Search - Workplace Relations Commission</title></head><body>
<div class="results-header"><p>0 results</p></div>
<ul></ul>
</body></html>
"""

DECISION_PAGE = b"""
<html><head><title>ADJ-00047352 - Workplace Relations Commission</title></head><body>
<div id="globalCookieBar" class="cookie">Our website uses cookies. I accept cookies from this site</div>
<header><div class="top-header">Workplace Relations</div></header>
<div class="container mb-4"><div class="container"><div class="row">
  <div class="col-sm-3"><a class="return-to-search" href="/en/search/">Return to Search</a></div>
  <div class="col-sm-9">
    <h1>ADJ-00047352</h1>
    <h2>Summary of Workers Case:</h2>
    <p>The worker submitted that the deduction from wages was not authorised.</p>
    <h2>Conclusions:</h2>
    <p>I find the complaint to be well founded.</p>
    <script>var tracking = 1;</script>
  </div>
</div></div></div>
<footer><div class="footer-two">Data Protection</div></footer>
<!-- cached location --><!-- Elapsed time: 0 -->
</body></html>
"""

# the same page as the site would serve it a second time: only the render time moved
DECISION_PAGE_RESERVED = DECISION_PAGE.replace(b"<!-- Elapsed time: 0 -->", b"<!-- Elapsed time: 0.0156031 -->")
