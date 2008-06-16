def menu(request, current):
     return [
      [current=='Portal', 'Home', '/'],
      [current=='Documents', 'Documents', '/documents'],
      [current=='Examples', 'Examples', '/examples'],
      [current=='About', 'About', '/about'],
    ]
    