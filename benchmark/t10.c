/*
 * file: t10.c
 * input: a in [30, 50]
 *        b in [90, 100]
 * output: j - i in [-10, 40]
 */


int foo(int a, int b) {


  int i = 0, j = 0;

  while(i < a){
	i++;
  } 
 
  do {
	j++;
  }while(i + j < b);


  return j - i;
}

