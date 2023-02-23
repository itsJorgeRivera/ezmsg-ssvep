// Define study
const study = lab.util.fromObject({
  "title": "root",
  "type": "lab.flow.Sequence",
  "parameters": {},
  "plugins": [
    {
      "type": "lab.plugins.Metadata",
      "path": undefined
    },
    {
      "type": "lab.plugins.Download",
      "filePrefix": "ssvep-stimulus",
      "path": undefined
    }
  ],
  "metadata": {
    "title": "SSVEP Stimulus",
    "description": "",
    "repository": "",
    "contributors": "Griffin Milsap \u003Cgriffin.milsap@jhuapl.edu\u003E (http:\u002F\u002Fwww.jhuapl.edu)"
  },
  "files": {},
  "responses": {},
  "content": [
    {
      "type": "lab.flow.Sequence",
      "files": {},
      "responses": {
        "": ""
      },
      "parameters": {},
      "messageHandlers": {
        "before:prepare": function anonymous(
) {
const urlParams = new URLSearchParams(window.location.search)
this.parameters.strobe_freq = parseFloat(urlParams.get('strobe_freq')) || 12.0
this.parameters.trials = parseInt(urlParams.get('trials')) || 10
this.parameters.trial_dur = parseInt(urlParams.get('trial_dur')) || 4000
this.parameters.isi_jitter = parseInt(urlParams.get('isi_jitter')) || 500
},
        "run": function anonymous(
) {
wsproto = ( 'https:' == document.location.protocol ) ? 'wss://' : 'ws://';    
window.socket = new WebSocket( wsproto + location.hostname + ':5545' );   
window.socket.onopen = () => console.log( 'Input Socket Connected' );
  
window.socket.onmessage = ( msg ) => {
  var content = JSON.parse( msg.data );
  for( var key in content )
    this.state[key] = content[key];
  this.commit();
};

window.transmit = function( obj ){
  if( window.socket )
    if( window.socket.readyState === window.socket.OPEN ) {
      window.socket.send( JSON.stringify( obj ) );
    }
};

this.internals.controller.datastore.on( 
  'commit', () => { 
    window.transmit( 
      { type: 'LOGJSON', value: this.state } 
    ); 
  } 
);

window.send_trigger = function( value, start, stop ) {
  console.log( 'Trigger:', value, start, stop );
  if( window.socket )
    if( window.socket.readyState === window.socket.OPEN ) {
      window.transmit( { 
        type: 'TRIGGER', 
        value: value, 
        start: start, 
        stop: stop 
      } );
    }
};

window.send_event = function( value ) {
  console.log( 'Event:', value );
  if( window.socket )
    if( window.socket.readyState === window.socket.OPEN ) {
      window.transmit( {
        type: 'EVENT',
        value: value
      } );
    }
};
}
      },
      "title": "SSVEP Stim",
      "content": [
        {
          "type": "lab.html.Form",
          "content": "\u003Cmain class=\"content-vertical-center content-horizontal-center\"\u003E\n  \u003Cform\u003E\n    \u003Ctable class=\"w-s text-left\"\u003E\n      \u003Ctr style=\"min-height: 80px\"\u003E\n        \u003Ctd class=\"text-right\"\u003EStrobe Frequency (Hz)\u003C\u002Ftd\u003E\n        \u003Ctd\u003E\n          \u003Cinput name=\"strobe_freq\" type=\"number\" value=\"${this.parameters.strobe_freq}\" min=\"1.0\" max=\"100.0\" step=\"0.1\"\u003E\n        \u003C\u002Ftd\u003E\n      \u003C\u002Ftr\u003E\n      \u003Ctr style=\"min-height: 80px\"\u003E\n        \u003Ctd class=\"text-right\"\u003ENumber of Trials\u003C\u002Ftd\u003E\n        \u003Ctd\u003E\n          \u003Cinput name=\"trials\" type=\"number\" value=\"${this.parameters.trials}\" min=\"1\" max=\"100\" step=\"1\"\u003E\n        \u003C\u002Ftd\u003E\n      \u003C\u002Ftr\u003E\n      \u003Ctr style=\"min-height: 80px\"\u003E\n        \u003Ctd class=\"text-right\"\u003ETrial\u002FStrobe Period (ms)\u003C\u002Ftd\u003E\n        \u003Ctd\u003E\n          \u003Cinput name=\"trial_dur\" type=\"number\" value=\"${this.parameters.trial_dur}\" min=\"0\" max=\"100000\" step=\"100\"\u003E\n        \u003C\u002Ftd\u003E\n      \u003C\u002Ftr\u003E\n      \u003Ctr style=\"min-height: 80px\"\u003E\n        \u003Ctd class=\"text-right\"\u003EInter-trial Jitter (ms)\u003C\u002Ftd\u003E\n        \u003Ctd\u003E\n          \u003Cinput name=\"isi_jitter\" type=\"number\" value=\"${this.parameters.isi_jitter}\" min=\"0\" max=\"100000\" step=\"100\"\u003E\n        \u003C\u002Ftd\u003E\n      \u003C\u002Ftr\u003E\n      \u003Ctr style=\"min-height: 80px\"\u003E\n        \u003Ctd class=\"text-right\" style=\"border-bottom: none\"\u003E\u003C\u002Ftd\u003E\n        \u003Ctd style=\"border-bottom: none\"\u003E\n          \u003Cbutton type=\"submit\" style=\"width: 100%\"\u003EContinue\u003C\u002Fbutton\u003E\n        \u003C\u002Ftd\u003E\n      \u003C\u002Ftr\u003E\n    \u003C\u002Ftable\u003E\n  \u003C\u002Fform\u003E\n\u003C\u002Fmain\u003E",
          "scrollTop": true,
          "files": {},
          "responses": {
            "": ""
          },
          "parameters": {},
          "messageHandlers": {
            "after:end": function anonymous(
) {
this.parent.parameters.strobe_freq = parseFloat( this.state.strobe_freq )
this.parent.parameters.trials = parseInt( this.state.trials )
this.parent.parameters.trial_dur = parseInt( this.state.trial_dur ) / 1000.0
this.parent.parameters.isi_jitter = parseInt( this.state.isi_jitter )

}
          },
          "title": "Task Settings"
        },
        {
          "type": "lab.html.Page",
          "items": [
            {
              "type": "text",
              "title": "SSVEP Stimulation",
              "content": "Stare at the dot in the center of the screen and try not to blink during the flashing periods."
            }
          ],
          "scrollTop": true,
          "submitButtonText": "Continue →",
          "submitButtonPosition": "right",
          "files": {},
          "responses": {
            "": ""
          },
          "parameters": {},
          "messageHandlers": {},
          "title": "Instructions"
        },
        {
          "type": "lab.html.Frame",
          "context": "\u003Cmain data-labjs-section=\"frame\"\u003E\n  \u003C!-- Content gets inserted here --\u003E\n\u003C\u002Fmain\u003E",
          "contextSelector": "[data-labjs-section=\"frame\"]",
          "files": {},
          "responses": {
            "": ""
          },
          "parameters": {},
          "messageHandlers": {},
          "title": "Task Frame",
          "content": {
            "type": "lab.flow.Loop",
            "templateParameters": [
              {
                "empty": "_",
                "": ""
              }
            ],
            "sample": {
              "mode": "draw",
              "n": "${parameters.trials}"
            },
            "files": {},
            "responses": {
              "": ""
            },
            "parameters": {},
            "messageHandlers": {},
            "title": "Trial Loop",
            "tardy": true,
            "indexParameter": "trial",
            "shuffleGroups": [],
            "template": {
              "type": "lab.flow.Sequence",
              "files": {},
              "responses": {
                "": ""
              },
              "parameters": {},
              "messageHandlers": {},
              "title": "Trial",
              "content": [
                {
                  "type": "lab.canvas.Screen",
                  "content": [
                    {
                      "type": "rect",
                      "left": 0,
                      "top": 0,
                      "angle": 0,
                      "width": "800",
                      "height": "600",
                      "stroke": null,
                      "strokeWidth": 1,
                      "fill": "#808080"
                    },
                    {
                      "type": "circle",
                      "left": 0,
                      "top": 0,
                      "angle": 0,
                      "width": "5",
                      "height": 55,
                      "stroke": null,
                      "strokeWidth": 1,
                      "fill": "#000000"
                    }
                  ],
                  "viewport": [
                    800,
                    600
                  ],
                  "files": {},
                  "responses": {
                    "": ""
                  },
                  "parameters": {},
                  "messageHandlers": {
                    "run": function anonymous(
) {
window.send_event('0');
},
                    "after:end": function anonymous(
) {
let label = this.parameters.strobe_freq.toString() + 'Hz';
window.send_event(label);
window.send_trigger(
  label, 
  -this.parameters.trial_dur, 
  this.parameters.trial_dur
);
}
                  },
                  "title": "Fixation",
                  "timeout": "${Math.floor(parameters.trial_dur*1000)}"
                },
                {
                  "type": "lab.flow.Loop",
                  "templateParameters": [
                    {
                      "also_empty": "_",
                      "": ""
                    }
                  ],
                  "sample": {
                    "mode": "draw",
                    "n": "${Math.floor(parameters.trial_dur*parameters.strobe_freq)}"
                  },
                  "files": {},
                  "responses": {
                    "": ""
                  },
                  "parameters": {},
                  "messageHandlers": {},
                  "title": "Strobe",
                  "indexParameter": "reversal",
                  "tardy": true,
                  "shuffleGroups": [],
                  "template": {
                    "type": "lab.canvas.Screen",
                    "content": [
                      {
                        "type": "rect",
                        "left": 0,
                        "top": 0,
                        "angle": 0,
                        "width": "800",
                        "height": "600",
                        "stroke": null,
                        "strokeWidth": 1,
                        "fill": "#808080"
                      },
                      {
                        "type": "rect",
                        "left": 375,
                        "top": 275,
                        "angle": 0,
                        "width": 50,
                        "height": 50,
                        "stroke": null,
                        "strokeWidth": 1,
                        "fill": "${parameters.reversal%2 ? 'white' : 'black'}"
                      },
                      {
                        "type": "image",
                        "left": 0,
                        "top": 0,
                        "angle": "${parameters.reversal%2 ? 0 : 7.5}",
                        "width": "720",
                        "height": "450",
                        "stroke": null,
                        "strokeWidth": 0,
                        "fill": "black",
                        "src": "${ this.files[\"radialCheckerboard.jpeg\"] }"
                      },
                      {
                        "type": "circle",
                        "left": 0,
                        "top": 0,
                        "angle": 0,
                        "width": "5",
                        "height": 55,
                        "stroke": null,
                        "strokeWidth": 1,
                        "fill": "${parameters.reversal%2 ? 'white' : 'black'}"
                      }
                    ],
                    "viewport": [
                      800,
                      600
                    ],
                    "files": {
                      "radialCheckerboard.jpeg": "embedded\u002F83007b33fa21a6b8c937e89899403e06041df5946828ff6d4c15b73ed3467dd2.jpeg"
                    },
                    "responses": {
                      "": ""
                    },
                    "parameters": {},
                    "messageHandlers": {},
                    "title": "Checker",
                    "timeout": "${Math.floor(1000.0\u002Fparameters.strobe_freq)}",
                    "tardy": true
                  }
                },
                {
                  "type": "lab.canvas.Screen",
                  "content": [
                    {
                      "type": "rect",
                      "left": 0,
                      "top": 0,
                      "angle": 0,
                      "width": "800",
                      "height": "600",
                      "stroke": null,
                      "strokeWidth": 1,
                      "fill": "#808080"
                    },
                    {
                      "type": "circle",
                      "left": 0,
                      "top": 0,
                      "angle": 0,
                      "width": "5",
                      "height": 55,
                      "stroke": null,
                      "strokeWidth": 1,
                      "fill": "black"
                    }
                  ],
                  "viewport": [
                    800,
                    600
                  ],
                  "files": {},
                  "responses": {
                    "": ""
                  },
                  "parameters": {},
                  "messageHandlers": {},
                  "title": "ISI",
                  "timeout": "${Math.floor(Math.random()*parameters.isi_jitter)}",
                  "tardy": true
                }
              ]
            }
          }
        }
      ]
    }
  ]
})

// Let's go!
study.run()