/*
 * file: t7.c
 * input: i in [-10, 10]
 * output: k in [16, 30]
 */


int bar(int i) {
   if(i >= 0) 
	return i + 10;
   else
	return -i + 5;
}

int foo(int i) {
  int j = bar(i);
  int k = bar(j); 
  return k;
}

