/*
 * file: t6.c
 * input: argc in [-inf, +inf]
 * output: sum in [-9, 10]
 */


int foo(int argc) {
  float i = 0.8, j = 10.2, sum = 0;
  if(argc){
     j = 9.2;
     sum = i + j;
  } else {
     i = 1.2;
     sum = i - j;
  }
  return sum;
}

