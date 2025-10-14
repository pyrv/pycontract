
* A DSL for Log Analysis

** Auction Example

This one does require recursion and an explicit state.

```
monitor Auction {
  case List(item?, reserve?): 
    Listed(item, reserve, 0)

  state Listed(item: str, reserve: int, prev_bid: int) {
    case Bid(item, amount?) if amount > prev_bid:
        Listed(item, reserve, amount)

    case Bid(item, amount?) if amount <= prev_bid:
      error(f'bid {amount} for item {self.item} is not above {self.prev_bid}')

    case Sell(item) if prev_bid > reserve:
      ok

    case Sell(item) if prev_bid <= reserve:
      error(f'item {self.item} sold below reserve {self.reserve}')
  }
}
```

** Lock Acquisitions and Releases

*** As a state machine:

```
monitor ShortAcquireRelease {
  case Acquire(thread?, lock?):
    Locked(thread, lock)

  hot Locked(thread: str, lock: int):
    case Acquire(_, lock):
      error('lock re-acquired')
    case Release(thread, lock):
      return ok
}
```

*** Inlining state as in Daut

```
monitor ShortAcquireRelease {
  case Acquire(thread?, lock?):
    hot {
      case Acquire(_, lock):
        error('lock re-acquired')
      case Release(thread, lock):
        return ok
    }
}
```

*** Temporal logic:

```
monitor ShortAcquireRelease {
  Acquire(thread?, lock?) 
  ->
  (!Acquire(_, lock),
     until  
    Release(thread, lock):
  )
}
```

*** LogScope style:

```
monitor ShortAcquireRelease {
  Acquire(thread?, lock?) 
  ->
  [
    !Acquire(_, lock),
    Release(thread, lock):
  ]
}
```

*** Timeline:

```
monitor ShortAcquireRelease {
  ?Acquire(thread?, lock?) 
  not Acquire(_, lock),
  !Release(thread, lock) 
}
```

*** Timeline generating higher level event:

```
monitor ShortAcquireRelease {
  ?Acquire(thread?, lock?) 
  not Acquire(_, lock),
  !Release(thread, lock) : Use(thread, lock)
}

Monitor NotTwice {
  Use(thread?,lock?),
  not Use(thread, lock)
}
```

*** RCAT 

**** P

```
monitor M {
  case e1: A

  hot A {
    case e2 : B
    case e4 : C
    case e5 : D
  }

  hot B {
    case e3 : ok
  }
  
  hot C {
    case e5 : ok
  }
  
  hot D {
    case e4 : ok
  }
}
```

**** D

```
monitor M {
  case e1: hot {
    case e2 : hot {
      case e3 : ok
      case e9 : error
    }
    case e4 : hot {
       case e5 : ok
    }
    case e5 : hot {
      case e4 : ok
    }
  }
}
```

**** D-

```
monitor M {
  case e1 {
    case e2 {
      case e3 
      veto e9
    }
    case e4 {
       case e5
    }
    case e5 {
      case e4
    }
  }
}
```

**** L

```
monitor M {
  e1 : or {
    [e2,!e9,e3]
    [e4, e5]
    [e5, e4]
  }
}
```

```
monitor M {
  e1 : hot {
    case e2 !e9 e3
    case e4 e5
    case e5 e4
  }
}
```


```
monitor M {
  case e1: hot {
    case e2 : hot {
      case e3 : hot {
         case e3 : ok
         case e5 : error 
      }
      case e9 : error
    }
  }
}
```

**** Time line ... becomes a tree

```
monitor M {
  e1?
  e2 
  not e9
  e3 
  not e5
  e3
}
```

```
monitor M {
  :: e1
     hot {
     :: e2; not e9; e3
     :: e4; e5
     :: e5; e4
     }
}
```

```
monitor M {
  :: e1 
     hot
     :: e2 
        hot
        :: e3 
           hot 
           :: e3
           :: not e5 
           end
        end
     :: not e9
     end
}
```

```
monitor M {
  :: e1 
     not e9
     e2
     e3
     not e5
     e3
}
```

```
monitor M {
  case e1 hot {
    case e2 hot {
      case e3 hot {
         case e3
         nada e5 
      }
      nada e9
    }
  }
}
```

