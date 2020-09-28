// Lib file for js used in CJS chrome extension
// (https://chrome.google.com/webstore/detail/custom-javascript-for-web/poakhlngfciodnhlhhgnaaelnpjljija?hl=en)

// sleep time expects milliseconds
function mySleep (time) {
  return new Promise((resolve) => setTimeout(resolve, time));
}

// Usage!
//mySleep(5000).then(() => {
// //Stuff here
//});
